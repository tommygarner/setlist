export default function ConcertCard({ concert, actions }) {
  const ticketUrl = concert.ticket_url || concert.url

  return (
    <div className="rounded-xl border border-white/10 bg-surface p-4 transition-colors hover:border-white/20">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-white">{concert.event_name}</p>
          <p className="mt-0.5 text-sm text-brand">{concert.artist_name}</p>
          <p className="mt-1 truncate text-xs text-gray-400">
            {concert.venue_name} · {concert.city}, {concert.state}
          </p>
          <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
            <span>📅 {concert.date}</span>
            {concert.time && <span>🕐 {concert.time}</span>}
            {concert.min_price && (
              <span>💰 ${concert.min_price}–${concert.max_price}</span>
            )}
            <span className="capitalize">{concert.source === 'seatgeek' ? '💺 SeatGeek' : '🎟️ Ticketmaster'}</span>
          </div>
        </div>

        <div className="flex flex-shrink-0 flex-col gap-2">
          {ticketUrl && (
            <a
              href={ticketUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-black transition-opacity hover:opacity-90"
            >
              Tickets
            </a>
          )}
          {actions}
        </div>
      </div>
    </div>
  )
}
