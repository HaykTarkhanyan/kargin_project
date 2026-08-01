import type { Song } from "@/lib/types";
import { formatDuration } from "@/lib/format";

/**
 * Music identified in a sketch's audio.
 *
 * Timestamps link out to YouTube at that second rather than seeking the embed:
 * this is a static export with no player bridge, so a real deep-link beats a
 * control that would not work.
 *
 * The orange time chips pin an explicit dark ink colour -- --orange is the same
 * #F2A800 in both themes, so themed ink would go near-white on orange.
 */
export default function SongList({ songs, watchUrl }: { songs: Song[]; watchUrl: string }) {
  if (!songs.length) return null;
  return (
    <ul className="space-y-2.5">
      {songs.map((song, i) => (
        <li key={`${song.artist}-${song.title}-${i}`} className="rounded-md border-2 border-ink bg-surface px-3 py-2">
          <div className="text-sm font-bold leading-snug">{song.title}</div>
          <div className="text-xs font-semibold text-muted">{song.artist}</div>
          {(song.label || song.released) && (
            <div className="mt-0.5 text-[11px] text-muted">
              {[song.label, song.released].filter(Boolean).join(" · ")}
            </div>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {song.at.map((sec) => (
              <a
                key={sec}
                href={`${watchUrl}?t=${sec}`}
                target="_blank"
                rel="noreferrer"
                title={`Դիտել ${formatDuration(sec)}-ից`}
                className="rounded border-[1.5px] border-ink bg-korange px-1.5 py-0.5 text-[11px] font-bold text-[#1A1410]"
              >
                ▶ {formatDuration(sec)}
              </a>
            ))}
            {song.url && (
              <a href={song.url} target="_blank" rel="noreferrer" className="text-[11px] font-semibold text-muted underline">
                Shazam
              </a>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
