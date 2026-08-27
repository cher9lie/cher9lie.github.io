export type Vector3 = [number, number, number]

const DEG = Math.PI / 180

function normalizeDegrees(value: number) {
  return ((value % 360) + 360) % 360
}

export function subsolarPoint(date = new Date()): [number, number] {
  const julianDate = date.getTime() / 86_400_000 + 2_440_587.5
  const days = julianDate - 2_451_545
  const meanLongitude = normalizeDegrees(280.46 + 0.9856474 * days)
  const meanAnomaly = normalizeDegrees(357.528 + 0.9856003 * days) * DEG
  const eclipticLongitude =
    (meanLongitude + 1.915 * Math.sin(meanAnomaly) + 0.02 * Math.sin(2 * meanAnomaly)) * DEG
  const obliquity = (23.439 - 0.0000004 * days) * DEG
  const declination = Math.asin(Math.sin(obliquity) * Math.sin(eclipticLongitude))
  const rightAscension = Math.atan2(
    Math.cos(obliquity) * Math.sin(eclipticLongitude),
    Math.cos(eclipticLongitude)
  )
  const siderealTime = normalizeDegrees(280.46061837 + 360.98564736629 * days) * DEG
  const longitude = Math.atan2(
    Math.sin(rightAscension - siderealTime),
    Math.cos(rightAscension - siderealTime)
  )

  return [longitude / DEG, declination / DEG]
}

export function solarVector(date = new Date()): Vector3 {
  const [longitude, latitude] = subsolarPoint(date)
  const lambda = longitude * DEG
  const phi = latitude * DEG
  const cosPhi = Math.cos(phi)
  return [cosPhi * Math.cos(lambda), Math.sin(phi), cosPhi * Math.sin(lambda)]
}
