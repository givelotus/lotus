# Prepared C5 prototype

Source migrations remove both private thread owners and adapt all seven call sites with unchanged logical chunk counts/boundaries. No utility/API/native RPC changes.

Tests add actual common-pool ownership/caller-thread assertions for contended and recursive signing work, inner exception transport and subsequent reuse; extend existing native+legacy signed fixture with failures outside chunk zero, exact earliest-index/legacy offset verdicts, and a last-chunk failure with more logical chunks than hardware. Overlay tests compare serial roots with batch roots/lookups across normal/contended/recursive execution including129 erasures/replacements and remove/readd of three transactions. Worker callbacks accumulate results; assertions remain on test thread. Fixture entries are copied per run because AddTransactionBatch consumes/moves its inputs, avoiding shared mutable test data.

ScopedParallelRangeBlocker is test-only cleanup ownership: release and join before assertions; future wait timeout releases blocked dispatch before reporting failure. No weakened existing assertion or source suppression. Root owns host; prototype is unbuilt/uncommitted until native C4 full and C5 gates pass.
