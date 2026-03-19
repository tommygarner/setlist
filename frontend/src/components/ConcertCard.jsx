export default function ConcertCard({ concert, actions }) {
  const rawUrl = concert.ticket_url || concert.url
  const ticketUrl = rawUrl && rawUrl.startsWith('http') ? rawUrl : null

  return (
    <div className="rounded-xl border border-white/10 bg-surface p-4 transition-colors hover:border-white/20">
      <div className="flex items-start gap-4">
        {concert.artist_image && (
          <img
            src={concert.artist_image}
            alt={concert.artist_name}
            className="h-14 w-14 flex-shrink-0 rounded-lg object-cover"
          />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="truncate font-semibold text-white">{concert.event_name}</p>
            {concert.score != null && (
              <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                concert.score >= 80
                  ? 'bg-brand/20 text-brand'
                  : concert.score >= 50
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'bg-white/10 text-gray-400'
              }`}>
                {Math.round(concert.score)}% match
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-brand">{concert.artist_name}</p>
          <p className="mt-1 truncate text-xs text-gray-400">
            {concert.venue_name} · {concert.city}, {concert.state}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            {concert.date && <span>📅 {concert.date}</span>}
            {concert.time && <span>🕐 {concert.time.slice(0, 5)}</span>}
            {concert.min_price && (
              <span>💰 ${concert.min_price}–${concert.max_price}</span>
            )}
            <span>{concert.source === 'seatgeek' ? '💺 SeatGeek' : '🎟 Ticketmaster'}</span>
          </div>
        </div>

        <div className="flex flex-shrink-0 flex-col gap-2">
          {ticketUrl ? (
            <a
              href={ticketUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-black transition-opacity hover:opacity-90"
            >
              Tickets
            </a>
          ) : (
            <span className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-600">
              No link
            </span>
          )}
          {actions}
        </div>
      </div>
    </div>
  )
}
