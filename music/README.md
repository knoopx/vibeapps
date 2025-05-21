# Music Player

* python
* gtk4
* libadwaita
* Search Entry on headerbar
* Screens
    * Albums List
    * Album Tracks
    * Playback Queue
* Classes
    * Release
    * Track
    * Scanner: find music files (*.{mp3,flac}). extracts metadata from filename patterns.

function replace(input: string, transforms = []) {
  return [
    [/(\([^\)]*\)?)+/gi, ''], // 'artist (...)' => 'artist'
    [/(\[[^\]]*\]?)+/gi, ''], // 'artist [...]' => 'artist'
    [/[_]+/g, ' '], // 'artist_name' => 'artist name'
    [/\s+/g, ' '], // '  ' => ' '
    [/\b\s*&\s*\b/gi, ' and '], // 'one & another' => 'one and another'
    [/\b([_'\-\s]+)n([_'\-\s])+\b/g, ' and '], // 'rock n roll' => 'rock and roll'
    ...transforms,
    [/^[_\-\s]+/gi, ''], // '- artist' => 'artist'
    [/[_\-\s]+$/gi, ''] // 'artist -' => 'artist'
  ].reduce((previous, [regex, value]) => {
    const result = previous.replace(regex, value)
    if (is.empty(result.trim())) { return value }
    return result
  }, input)
}

export function string(input: string) {
  return replace(input)
}

export function albumName(input: string) {
  return replace(string(input).replace(/^([\w\s]+\w)\-[A-Z0-9][A-Z0-9]+.+$/g, '$1'), [
    [/\b(TRACKFIX|DIRFIX|READ[\-\s]*NFO)\b/gi, ''],
    [/\b\d+[\-\s]*(inch|"|i)(\s*vinyl)?\b/i, ''],
    [/\b(S[\-\_\s\.]*T[\-\_\s\.]|SELF[\-\_\s\.]*TITLED)\b/i, 'Self-Titled'],
    [/\b((RE[\-\s]*)?(MASTERED|ISSUE|PACKAGE|EDITION))\b/gi, ''],
    [/\b(ADVANCE|PROMO|SAMPLER|PROPER|RERIP|RETAIL|REMIX|BONUS|LTD\.?|LIMITED)\b/gi, ''],
    [/\b(CDM|CDEP|CDR|CDS|CD|MCD|DVDA|DVD|TAPE|VINYL|VLS|WEB|SAT|CABLE)\b/g, ''],
    [/\b(EP|LP|BOOTLEG|SINGLE)\b/gi, '']
  ])
}

export function artistName(input: string) {
  return replace(input, [
    [/\b(ft|feat|presents)[\_\-\s\.]+.+$/i, '']
  ])
}

export function genre(input: string) {
  const expected = fingerprint(input)
  return genres.find(g => fingerprint(g) === expected)
}

export function tags(input: string) {
  const regex = {
    Vinyl: /\b(VINYL|VLS)\b/i,
    CD: /\b(CDM|CDEP|CDR|CDS|CD|MCD)\b/i,
    DVD: /\b(DVDA|DVD)\b/i,
    Cassette: /\b(TAPE)\b/i,
    File: /\b(WEB)\b/i,
    'Limited Edition': /\b(LTD\.?|LIMITED)\b/i,
    Remastered: /\b(REMASTERED)\b/i,
    Reissue: /\b(REISSUE)\b/i,
    Advance: /\b(ADVANCE)\b/i,
    Promo: /\b(PROMO)\b/i,
    Rerip: /\b(RERIP)\b/i,
    Remix: /\b(REMIX|RMX)\b/i,
    Proper: /\b(PROPER)\b/i,
    Retail: /\b(RETAIL)\b/i,
    Sampler: /\b(SAMPLER)\b/i,
    EP: /\b(EP)\b/i,
    LP: /\b(LP)\b/i,
    Bootleg: /\b(BOOTLEG)\b/i,
    Single: /\b(SINGLE|VLS|CDS)\b/i,
    Compilation: /^VA-/
  }
  return Object.keys(regex).filter(key => regex[key].test(input))
}
