package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

const cacheTTL = 5 * time.Minute

type dailyStat struct {
	Day   string `json:"day"`
	Daily int    `json:"daily"`
}

type totalResponse struct {
	Total int         `json:"total"`
	Stats []dailyStat `json:"stats"`
}

type hitStat struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Count int    `json:"count"`
}

type statsResponse struct {
	Stats []hitStat `json:"stats"`
}

type hit struct {
	Count int    `json:"count"`
	Path  string `json:"path"`
	Event bool   `json:"event"`
	Title string `json:"title"`
}

type hitsResponse struct {
	Hits []hit `json:"hits"`
}

type publicSummary struct {
	Period    string         `json:"period"`
	Start     string         `json:"start"`
	UpdatedAt string         `json:"updated_at"`
	Totals    publicTotals   `json:"totals"`
	Series    []publicDaily  `json:"series"`
	Countries []publicCountry `json:"countries"`
	Pages     []publicPage   `json:"pages"`
}

type publicTotals struct {
	Visits    int `json:"visits"`
	Countries int `json:"countries"`
	Pages     int `json:"pages"`
}

type publicDaily struct {
	Date   string `json:"date"`
	Visits int    `json:"visits"`
}

type publicCountry struct {
	Code   string `json:"code"`
	Name   string `json:"name"`
	Visits int    `json:"visits"`
}

type publicPage struct {
	Path   string `json:"path"`
	Title  string `json:"title"`
	Visits int    `json:"visits"`
}

type cacheEntry struct {
	data      publicSummary
	expiresAt time.Time
}

type server struct {
	baseURL       string
	host          string
	token         string
	start         time.Time
	allowedOrigin map[string]bool
	client        *http.Client
	cacheMu       sync.Mutex
	cache         map[string]cacheEntry
}

func main() {
	token := strings.TrimSpace(os.Getenv("GOATCOUNTER_API_TOKEN"))
	if token == "" {
		log.Fatal("GOATCOUNTER_API_TOKEN is required")
	}

	start := time.Date(2026, 8, 22, 0, 0, 0, 0, time.UTC)
	if raw := strings.TrimSpace(os.Getenv("STATS_START")); raw != "" {
		parsed, err := time.Parse(time.RFC3339, raw)
		if err != nil {
			log.Fatalf("invalid STATS_START: %v", err)
		}
		start = parsed.UTC()
	}

	allowed := make(map[string]bool)
	for _, origin := range strings.Split(envOr("STATS_ALLOWED_ORIGINS", "https://050418.xyz"), ",") {
		allowed[strings.TrimSpace(origin)] = true
	}

	s := &server{
		baseURL:       strings.TrimRight(envOr("GOATCOUNTER_BASE_URL", "http://goatcounter:8080"), "/"),
		host:          envOr("GOATCOUNTER_HOST", "stats.050418.xyz"),
		token:         token,
		start:         start,
		allowedOrigin: allowed,
		client:        &http.Client{Timeout: 12 * time.Second},
		cache:         make(map[string]cacheEntry),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("/v1/summary", s.handleSummary)

	log.Printf("public statistics API listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}

func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func (s *server) handleSummary(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "public, max-age=300, stale-while-revalidate=60")
	origin := r.Header.Get("Origin")
	if origin != "" && s.allowedOrigin[origin] {
		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Set("Vary", "Origin")
	}
	if r.Method == http.MethodOptions {
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.WriteHeader(http.StatusNoContent)
		return
	}
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	period := r.URL.Query().Get("period")
	if period == "" {
		period = "30d"
	}
	if period != "7d" && period != "30d" && period != "all" {
		http.Error(w, "unsupported period", http.StatusBadRequest)
		return
	}

	if data, ok := s.cached(period); ok {
		writeJSON(w, data)
		return
	}

	data, err := s.loadSummary(r.Context(), period)
	if err != nil {
		log.Printf("load summary: %v", err)
		http.Error(w, "statistics temporarily unavailable", http.StatusBadGateway)
		return
	}

	s.cacheMu.Lock()
	s.cache[period] = cacheEntry{data: data, expiresAt: time.Now().Add(cacheTTL)}
	s.cacheMu.Unlock()
	writeJSON(w, data)
}

func (s *server) cached(period string) (publicSummary, bool) {
	s.cacheMu.Lock()
	defer s.cacheMu.Unlock()
	entry, ok := s.cache[period]
	return entry.data, ok && time.Now().Before(entry.expiresAt)
}

func (s *server) loadSummary(ctx context.Context, period string) (publicSummary, error) {
	now := time.Now().UTC()
	start := s.start
	switch period {
	case "7d":
		start = now.AddDate(0, 0, -6).Truncate(24 * time.Hour)
	case "30d":
		start = now.AddDate(0, 0, -29).Truncate(24 * time.Hour)
	}

	var totals totalResponse
	var locations statsResponse
	var pages hitsResponse
	errCh := make(chan error, 3)
	var wg sync.WaitGroup
	queries := []struct {
		path   string
		limit  int
		target any
	}{
		{path: "/api/v0/stats/total", target: &totals},
		{path: "/api/v0/stats/locations", limit: 100, target: &locations},
		{path: "/api/v0/stats/hits", limit: 20, target: &pages},
	}

	for _, query := range queries {
		query := query
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := s.fetch(ctx, query.path, start, query.limit, query.target); err != nil {
				errCh <- err
			}
		}()
	}
	wg.Wait()
	close(errCh)
	for err := range errCh {
		if err != nil {
			return publicSummary{}, err
		}
	}

	series := make([]publicDaily, 0, len(totals.Stats))
	for _, stat := range totals.Stats {
		series = append(series, publicDaily{Date: stat.Day, Visits: stat.Daily})
	}

	countries := make([]publicCountry, 0, len(locations.Stats))
	for _, country := range locations.Stats {
		code := strings.ToUpper(country.ID)
		if len(code) != 2 || country.Count < 1 {
			continue
		}
		countries = append(countries, publicCountry{Code: code, Name: country.Name, Visits: country.Count})
	}
	sort.Slice(countries, func(i, j int) bool { return countries[i].Visits > countries[j].Visits })

	publicPages := make([]publicPage, 0, 8)
	for _, page := range pages.Hits {
		if page.Event || page.Path == "/stats" || page.Path == "/404" || len(publicPages) >= 8 {
			continue
		}
		title := strings.TrimSuffix(page.Title, " • Cher9lie's Blog&Docs")
		publicPages = append(publicPages, publicPage{Path: page.Path, Title: title, Visits: page.Count})
	}

	return publicSummary{
		Period:    period,
		Start:     start.Format(time.RFC3339),
		UpdatedAt: now.Format(time.RFC3339),
		Totals: publicTotals{
			Visits:    totals.Total,
			Countries: len(countries),
			Pages:     len(publicPages),
		},
		Series:    series,
		Countries: countries,
		Pages:     publicPages,
	}, nil
}

func (s *server) fetch(ctx context.Context, path string, start time.Time, limit int, target any) error {
	endpoint, err := url.Parse(s.baseURL + path)
	if err != nil {
		return err
	}
	query := endpoint.Query()
	query.Set("start", start.Format(time.RFC3339))
	if limit > 0 {
		query.Set("limit", fmt.Sprint(limit))
	}
	endpoint.RawQuery = query.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
	if err != nil {
		return err
	}
	req.Host = s.host
	req.Header.Set("Authorization", "Bearer "+s.token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("%s returned %s", path, resp.Status)
	}
	if err := json.NewDecoder(resp.Body).Decode(target); err != nil {
		return err
	}
	return nil
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	if err := json.NewEncoder(w).Encode(value); err != nil && !errors.Is(err, context.Canceled) {
		log.Printf("write response: %v", err)
	}
}
