// Site timezone utilities for frontend
export const SITE_TZ = 'America/Los_Angeles';

export type TimeRange = 'today' | 'last_24h' | 'this_week' | 'this_month' | 'this_year' | 'last_7_days' | 'last_30_days';

export const TIME_RANGES: Record<TimeRange, string> = {
  today: '今天',
  last_24h: '最近24小时',
  this_week: '本周',
  this_month: '本月',
  this_year: '本年',
  last_7_days: '最近7天',
  last_30_days: '最近30天',
};

export function toSiteTime(date: Date, site = 'US'): Date {
  const tz = site === 'US' ? SITE_TZ : SITE_TZ;
  const str = date.toLocaleString('en-US', { timeZone: tz });
  return new Date(str);
}

export function formatSiteTime(date: Date, format?: 'date' | 'datetime' | 'time'): string {
  const opts: Intl.DateTimeFormatOptions = {
    timeZone: SITE_TZ,
    ...(format === 'date' ? { year: 'numeric', month: '2-digit', day: '2-digit' } :
       format === 'time' ? { hour: '2-digit', minute: '2-digit', second: '2-digit' } :
       { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
  };
  return new Intl.DateTimeFormat('zh-CN', opts).format(date);
}

export function getTimeRangeLabel(range: TimeRange): string {
  return TIME_RANGES[range] ?? range;
}
