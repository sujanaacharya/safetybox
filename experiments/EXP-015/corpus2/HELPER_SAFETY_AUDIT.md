# Helper safety audit

The only helper source is emitted by the frozen v2 materializer from a closed
`HelperBehavior` enum. It uses native argv, never invokes a shell, never accepts
an executable name, and has no network or privilege operation. Its writes are
only declared marker paths under the supplied temporary materialization root.
Sleep duration is an explicit bounded integer recipe; no fork, recursion, or
unbounded output behavior is authored. The corpus materialization gate does not
execute helpers.
