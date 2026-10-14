// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'rpc.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

RPCRequest _$RPCRequestFromJson(Map<String, dynamic> json) {
  $checkKeys(json, disallowNullValues: const ['method']);
  return RPCRequest(
    json['method'] as String?,
    id: (json['id'] as num?)?.toInt(),
    params: json['params'],
  );
}

Map<String, dynamic> _$RPCRequestToJson(RPCRequest instance) =>
    <String, dynamic>{
      'method': ?instance.method,
      'id': instance.id,
      'params': instance.params,
    };

Error _$ErrorFromJson(Map<String, dynamic> json) {
  $checkKeys(json, disallowNullValues: const ['code', 'message']);
  return Error(
    (json['code'] as num?)?.toInt(),
    json['message'] as String?,
    data: json['data'],
  );
}

Map<String, dynamic> _$ErrorToJson(Error instance) => <String, dynamic>{
  'code': ?instance.code,
  'message': ?instance.message,
  'data': instance.data,
};

RPCResponse _$RPCResponseFromJson(Map<String, dynamic> json) {
  $checkKeys(json, disallowNullValues: const ['id']);
  return RPCResponse(
    json['result'],
    id: (json['id'] as num?)?.toInt(),
    error: json['error'] == null
        ? null
        : Error.fromJson(json['error'] as Map<String, dynamic>),
  );
}

Map<String, dynamic> _$RPCResponseToJson(RPCResponse instance) =>
    <String, dynamic>{
      'result': instance.result,
      'error': instance.error,
      'id': ?instance.id,
    };
