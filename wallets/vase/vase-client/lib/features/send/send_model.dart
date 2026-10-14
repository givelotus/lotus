import 'package:flutter/foundation.dart';

const maxLength = 7;

class SendModel extends ChangeNotifier {
  BigInt _amount = BigInt.zero;
  String _address = '';

  BigInt get amount => _amount;
  String get address => _address;

  void setPayment(String address, BigInt amount) {
    if (amount < BigInt.zero) throw ArgumentError.value(amount, 'amount');
    _address = address;
    _amount = amount;
    notifyListeners();
  }

  void clear() => setPayment('', BigInt.zero);

  void setAmount(BigInt amount) {
    _amount = amount;
    notifyListeners();
  }

  void setAddress(String address) {
    _address = address;
    notifyListeners();
  }
}
