# Profiles

A site profile tells the SEO skills what your business is, so reports come back
specific rather than generic. `example-profile.md` here is a fictional worked
example.

**Do not keep your real profile in this folder.** Plugin directories are
replaced wholesale when the plugin updates, so anything stored here is lost on
the next version bump — and a real profile contains competitor targeting and
page priorities you probably do not want in a shared repo.

Put it with the site it describes (`docs/seo-profile.md` in that site's repo is
ideal), then point Claude at it:

> Analyze last month's Search Console data using the profile at
> `~/work/website/docs/seo-profile.md`

To build one from scratch, ask Claude to "set up my site profile" — the
`gsc-site-profile` skill derives most of it from your existing GSC data and asks
only for what it cannot infer.
