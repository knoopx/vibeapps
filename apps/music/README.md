```bash
find . -type f -iname '*.nfo' -exec grep -l -i "screamo" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Screamo.json

find . -type f -iname '*.nfo' -exec grep -l -i "mathrock" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Mathrock.json

find . -type f -iname '*.nfo' -exec grep -l -i "blue note" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Blue Note.json

find . -type f -iname '*.nfo' -exec grep -l -i "colmine" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Blue Note.json


find . -type f -iname '*.nfo' -exec grep -l -i "punk" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Punk.json
find . -type f -iname '*.nfo' -exec grep -l -i "hardcore" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Hardcore.json
find . -type f -iname '*.nfo' -exec grep -l -i "post-hardcore" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Post\ Hardcore.json
find . -type f -iname '*.nfo' -exec grep -l -i "metal" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Metal.json
find . -type f -iname '*.nfo' -exec grep -l -i "boogaloo" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Boogaloo.json
find . -type f -iname '*.nfo' -exec grep -l -i "funk" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Funk.json
find . -type f -iname '*.nfo' -exec grep -l -i "hip-hop" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Hip-Hop.json

find . -type f -iname '*.nfo' -exec grep -l -i "folk" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Folk.json

find . -type f -iname '*.nfo' -exec grep -l -i "pop" {} + | xargs -n1 dirname | xargs -n1 basename | jq -R 'ascii_downcase' | jq -s . > ~/.config/net.knoopx.music/collections/Pop.json

```


# TODO

* show title tip on hover
- sidebar + play queue?
- rateyourmusic/discogs
