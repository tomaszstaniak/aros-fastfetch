# Source and patch workflow

upstreams.json pins the upstream source. Keep upstream/fastfetch clean at that
commit. Make changes in work/fastfetch, then export them to patches/fastfetch and
list them in application order in series. An empty series means unmodified upstream.

Before claiming reproducibility, reconstruct a fresh tree from the pin and apply
the entire series. Compare it with the intended source tree and build it. Work-copy
commits alone are not the port record. Preserve licenses in exported changes.

Never reconstruct over unexported edits. Remove disposable verification trees
after recording results and hashes.
