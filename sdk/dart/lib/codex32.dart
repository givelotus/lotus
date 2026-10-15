/// Browser-safe Codex32 and typed Frank recovery-share backup primitives.
///
/// Adapted from Frank's MIT-licensed Codex32 and account-recovery packages.
/// See docs/codex32.md for source revisions and format boundaries.
/// These formats are distinct: ms1 is BIP93; fr1 carries a typed recovery secret.
library;

export 'src/backup/codex32.dart';
export 'src/backup/frank_recovery.dart';
