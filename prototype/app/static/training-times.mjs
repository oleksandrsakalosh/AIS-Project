const bratislava = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Bratislava', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
});
const slovakDate = new Intl.DateTimeFormat('sk-SK', {
  timeZone: 'Europe/Bratislava', weekday: 'long', day: 'numeric', month: 'long'
});

export function bratislavaWall(instant) {
  const parts = Object.fromEntries(bratislava.formatToParts(new Date(instant)).map(part => [part.type, part.value]));
  return [parts.year.padStart(4, '0'), parts.month, parts.day].join('-') + 'T' +
    [parts.hour, parts.minute, parts.second].join(':');
}

export function instantChoices(value) {
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?$/.test(value)) return [];
  const wall = value.length === 16 ? value + ':00' : value;
  const nominal = Date.parse(wall + 'Z');
  if (!Number.isFinite(nominal)) return [];
  // Bratislava’s offset on either side of a clock change supplies the two possible candidates.
  const day = 86400000;
  const offsets = new Set([nominal - day, nominal, nominal + day].map(sample =>
    Date.parse(bratislavaWall(sample) + 'Z') - sample).filter(Number.isFinite));
  return [...offsets].map(offset => ({offset, instant: new Date(nominal - offset).toISOString()}))
    .filter(choice => bratislavaWall(choice.instant) === wall)
    .sort((first, second) => first.instant.localeCompare(second.instant));
}

export function offsetLabel(offset) {
  const minutes = Math.abs(offset) / 60000;
  return 'UTC' + (offset < 0 ? '−' : '+') +
    String(Math.floor(minutes / 60)).padStart(2, '0') + ':' + String(minutes % 60).padStart(2, '0');
}

export function bratislavaDate(value) {
  return slovakDate.format(new Date(value));
}

export function bratislavaTime(value) {
  const wall = bratislavaWall(value);
  const alternatives = instantChoices(wall);
  const shown = wall.slice(11, wall.endsWith(':00') ? 16 : 19);
  const choice = alternatives.find(candidate =>
    Date.parse(candidate.instant) === Math.floor(Date.parse(value) / 1000) * 1000);
  return alternatives.length > 1 && choice ? shown + ' ' + offsetLabel(choice.offset) : shown;
}

export function trainingTime({starts_at, ends_at}) {
  const endDate = bratislavaWall(starts_at).slice(0, 10) !== bratislavaWall(ends_at).slice(0, 10)
    ? bratislavaDate(ends_at) + ' ' : '';
  return bratislavaTime(starts_at) + ' — ' + endDate + bratislavaTime(ends_at);
}
