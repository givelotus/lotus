import 'package:lotus_dart/lotus.dart';
import 'package:lotus_dart/chronik.dart' as chronik;

void main() {
  print(lotusTxId([0, 0, 0, 0, 0, 0, 0, 0, 0, 0]));
  final client = chronik.ChronikClient('https://example.invalid');
  client.close();
}
