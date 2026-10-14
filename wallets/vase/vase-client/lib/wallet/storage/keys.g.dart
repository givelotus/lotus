// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'keys.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

KeyStorageMetadata _$KeyStorageMetadataFromJson(Map<String, dynamic> json) =>
    KeyStorageMetadata((json['keyCount'] as num?)?.toInt());

Map<String, dynamic> _$KeyStorageMetadataToJson(KeyStorageMetadata instance) =>
    <String, dynamic>{'keyCount': instance.keyCount};

StoredKey _$StoredKeyFromJson(Map<String, dynamic> json) =>
    StoredKey(json['privateKey'] as String?, json['isChange'] as bool?);

Map<String, dynamic> _$StoredKeyToJson(StoredKey instance) => <String, dynamic>{
  'privateKey': instance.privateKey,
  'isChange': instance.isChange,
};
