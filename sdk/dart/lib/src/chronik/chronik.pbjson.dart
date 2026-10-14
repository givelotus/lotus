// This is a generated file - do not edit.
//
// Generated from chronik.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports
// ignore_for_file: unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use tokenStatusDescriptor instead')
const TokenStatus$json = {
  '1': 'TokenStatus',
  '2': [
    {'1': 'TOKEN_STATUS_NON_TOKEN', '2': 0},
    {'1': 'TOKEN_STATUS_NORMAL', '2': 1},
    {'1': 'TOKEN_STATUS_NOT_NORMAL', '2': 2},
  ],
};

/// Descriptor for `TokenStatus`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List tokenStatusDescriptor = $convert.base64Decode(
    'CgtUb2tlblN0YXR1cxIaChZUT0tFTl9TVEFUVVNfTk9OX1RPS0VOEAASFwoTVE9LRU5fU1RBVF'
    'VTX05PUk1BTBABEhsKF1RPS0VOX1NUQVRVU19OT1RfTk9STUFMEAI=');

@$core.Deprecated('Use alpTokenTypeDescriptor instead')
const AlpTokenType$json = {
  '1': 'AlpTokenType',
  '2': [
    {'1': 'ALP_TOKEN_TYPE_STANDARD', '2': 0},
  ],
};

/// Descriptor for `AlpTokenType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List alpTokenTypeDescriptor = $convert.base64Decode(
    'CgxBbHBUb2tlblR5cGUSGwoXQUxQX1RPS0VOX1RZUEVfU1RBTkRBUkQQAA==');

@$core.Deprecated('Use slpTokenTypeDescriptor instead')
const SlpTokenType$json = {
  '1': 'SlpTokenType',
  '2': [
    {'1': 'SLP_TOKEN_TYPE_NONE', '2': 0},
    {'1': 'SLP_TOKEN_TYPE_FUNGIBLE', '2': 1},
    {'1': 'SLP_TOKEN_TYPE_MINT_VAULT', '2': 2},
    {'1': 'SLP_TOKEN_TYPE_NFT1_GROUP', '2': 129},
    {'1': 'SLP_TOKEN_TYPE_NFT1_CHILD', '2': 65},
  ],
};

/// Descriptor for `SlpTokenType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List slpTokenTypeDescriptor = $convert.base64Decode(
    'CgxTbHBUb2tlblR5cGUSFwoTU0xQX1RPS0VOX1RZUEVfTk9ORRAAEhsKF1NMUF9UT0tFTl9UWV'
    'BFX0ZVTkdJQkxFEAESHQoZU0xQX1RPS0VOX1RZUEVfTUlOVF9WQVVMVBACEh4KGVNMUF9UT0tF'
    'Tl9UWVBFX05GVDFfR1JPVVAQgQESHQoZU0xQX1RPS0VOX1RZUEVfTkZUMV9DSElMRBBB');

@$core.Deprecated('Use tokenTxTypeDescriptor instead')
const TokenTxType$json = {
  '1': 'TokenTxType',
  '2': [
    {'1': 'NONE', '2': 0},
    {'1': 'UNKNOWN', '2': 1},
    {'1': 'GENESIS', '2': 2},
    {'1': 'SEND', '2': 3},
    {'1': 'MINT', '2': 4},
    {'1': 'BURN', '2': 5},
  ],
};

/// Descriptor for `TokenTxType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List tokenTxTypeDescriptor = $convert.base64Decode(
    'CgtUb2tlblR4VHlwZRIICgROT05FEAASCwoHVU5LTk9XThABEgsKB0dFTkVTSVMQAhIICgRTRU'
    '5EEAMSCAoETUlOVBAEEggKBEJVUk4QBQ==');

@$core.Deprecated('Use blockMsgTypeDescriptor instead')
const BlockMsgType$json = {
  '1': 'BlockMsgType',
  '2': [
    {'1': 'BLK_CONNECTED', '2': 0},
    {'1': 'BLK_DISCONNECTED', '2': 1},
    {'1': 'BLK_FINALIZED', '2': 2},
    {'1': 'BLK_INVALIDATED', '2': 3},
  ],
};

/// Descriptor for `BlockMsgType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List blockMsgTypeDescriptor = $convert.base64Decode(
    'CgxCbG9ja01zZ1R5cGUSEQoNQkxLX0NPTk5FQ1RFRBAAEhQKEEJMS19ESVNDT05ORUNURUQQAR'
    'IRCg1CTEtfRklOQUxJWkVEEAISEwoPQkxLX0lOVkFMSURBVEVEEAM=');

@$core.Deprecated('Use txFinalizationReasonTypeDescriptor instead')
const TxFinalizationReasonType$json = {
  '1': 'TxFinalizationReasonType',
  '2': [
    {'1': 'TX_FINALIZATION_REASON_POST_CONSENSUS', '2': 0},
    {'1': 'TX_FINALIZATION_REASON_PRE_CONSENSUS', '2': 1},
  ],
};

/// Descriptor for `TxFinalizationReasonType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List txFinalizationReasonTypeDescriptor = $convert.base64Decode(
    'ChhUeEZpbmFsaXphdGlvblJlYXNvblR5cGUSKQolVFhfRklOQUxJWkFUSU9OX1JFQVNPTl9QT1'
    'NUX0NPTlNFTlNVUxAAEigKJFRYX0ZJTkFMSVpBVElPTl9SRUFTT05fUFJFX0NPTlNFTlNVUxAB');

@$core.Deprecated('Use txMsgTypeDescriptor instead')
const TxMsgType$json = {
  '1': 'TxMsgType',
  '2': [
    {'1': 'TX_ADDED_TO_MEMPOOL', '2': 0},
    {'1': 'TX_REMOVED_FROM_MEMPOOL', '2': 1},
    {'1': 'TX_CONFIRMED', '2': 2},
    {'1': 'TX_FINALIZED', '2': 3},
    {'1': 'TX_INVALIDATED', '2': 4},
  ],
};

/// Descriptor for `TxMsgType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List txMsgTypeDescriptor = $convert.base64Decode(
    'CglUeE1zZ1R5cGUSFwoTVFhfQURERURfVE9fTUVNUE9PTBAAEhsKF1RYX1JFTU9WRURfRlJPTV'
    '9NRU1QT09MEAESEAoMVFhfQ09ORklSTUVEEAISEAoMVFhfRklOQUxJWkVEEAMSEgoOVFhfSU5W'
    'QUxJREFURUQQBA==');

@$core.Deprecated('Use blockDescriptor instead')
const Block$json = {
  '1': 'Block',
  '2': [
    {
      '1': 'block_info',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.BlockInfo',
      '10': 'blockInfo'
    },
  ],
};

/// Descriptor for `Block`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockDescriptor = $convert.base64Decode(
    'CgVCbG9jaxIxCgpibG9ja19pbmZvGAEgASgLMhIuY2hyb25pay5CbG9ja0luZm9SCWJsb2NrSW'
    '5mbw==');

@$core.Deprecated('Use blocksDescriptor instead')
const Blocks$json = {
  '1': 'Blocks',
  '2': [
    {
      '1': 'blocks',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.BlockInfo',
      '10': 'blocks'
    },
  ],
};

/// Descriptor for `Blocks`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blocksDescriptor = $convert.base64Decode(
    'CgZCbG9ja3MSKgoGYmxvY2tzGAEgAygLMhIuY2hyb25pay5CbG9ja0luZm9SBmJsb2Nrcw==');

@$core.Deprecated('Use blockHeaderDescriptor instead')
const BlockHeader$json = {
  '1': 'BlockHeader',
  '2': [
    {'1': 'raw_header', '3': 1, '4': 1, '5': 12, '10': 'rawHeader'},
    {'1': 'root', '3': 2, '4': 1, '5': 12, '10': 'root'},
    {'1': 'branch', '3': 3, '4': 3, '5': 12, '10': 'branch'},
  ],
};

/// Descriptor for `BlockHeader`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockHeaderDescriptor = $convert.base64Decode(
    'CgtCbG9ja0hlYWRlchIdCgpyYXdfaGVhZGVyGAEgASgMUglyYXdIZWFkZXISEgoEcm9vdBgCIA'
    'EoDFIEcm9vdBIWCgZicmFuY2gYAyADKAxSBmJyYW5jaA==');

@$core.Deprecated('Use blockHeadersDescriptor instead')
const BlockHeaders$json = {
  '1': 'BlockHeaders',
  '2': [
    {
      '1': 'headers',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.BlockHeader',
      '10': 'headers'
    },
  ],
};

/// Descriptor for `BlockHeaders`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockHeadersDescriptor = $convert.base64Decode(
    'CgxCbG9ja0hlYWRlcnMSLgoHaGVhZGVycxgBIAMoCzIULmNocm9uaWsuQmxvY2tIZWFkZXJSB2'
    'hlYWRlcnM=');

@$core.Deprecated('Use blockchainInfoDescriptor instead')
const BlockchainInfo$json = {
  '1': 'BlockchainInfo',
  '2': [
    {'1': 'tip_hash', '3': 1, '4': 1, '5': 12, '10': 'tipHash'},
    {'1': 'tip_height', '3': 2, '4': 1, '5': 5, '10': 'tipHeight'},
  ],
};

/// Descriptor for `BlockchainInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockchainInfoDescriptor = $convert.base64Decode(
    'Cg5CbG9ja2NoYWluSW5mbxIZCgh0aXBfaGFzaBgBIAEoDFIHdGlwSGFzaBIdCgp0aXBfaGVpZ2'
    'h0GAIgASgFUgl0aXBIZWlnaHQ=');

@$core.Deprecated('Use chronikInfoDescriptor instead')
const ChronikInfo$json = {
  '1': 'ChronikInfo',
  '2': [
    {'1': 'version', '3': 1, '4': 1, '5': 9, '10': 'version'},
  ],
};

/// Descriptor for `ChronikInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List chronikInfoDescriptor = $convert
    .base64Decode('CgtDaHJvbmlrSW5mbxIYCgd2ZXJzaW9uGAEgASgJUgd2ZXJzaW9u');

@$core.Deprecated('Use blockInfoDescriptor instead')
const BlockInfo$json = {
  '1': 'BlockInfo',
  '2': [
    {'1': 'hash', '3': 1, '4': 1, '5': 12, '10': 'hash'},
    {'1': 'prev_hash', '3': 2, '4': 1, '5': 12, '10': 'prevHash'},
    {'1': 'height', '3': 3, '4': 1, '5': 5, '10': 'height'},
    {'1': 'n_bits', '3': 4, '4': 1, '5': 13, '10': 'nBits'},
    {'1': 'timestamp', '3': 5, '4': 1, '5': 3, '10': 'timestamp'},
    {'1': 'is_final', '3': 14, '4': 1, '5': 8, '10': 'isFinal'},
    {'1': 'block_size', '3': 6, '4': 1, '5': 4, '10': 'blockSize'},
    {'1': 'num_txs', '3': 7, '4': 1, '5': 4, '10': 'numTxs'},
    {'1': 'num_inputs', '3': 8, '4': 1, '5': 4, '10': 'numInputs'},
    {'1': 'num_outputs', '3': 9, '4': 1, '5': 4, '10': 'numOutputs'},
    {'1': 'sum_input_sats', '3': 10, '4': 1, '5': 3, '10': 'sumInputSats'},
    {
      '1': 'sum_coinbase_output_sats',
      '3': 11,
      '4': 1,
      '5': 3,
      '10': 'sumCoinbaseOutputSats'
    },
    {
      '1': 'sum_normal_output_sats',
      '3': 12,
      '4': 1,
      '5': 3,
      '10': 'sumNormalOutputSats'
    },
    {'1': 'sum_burned_sats', '3': 13, '4': 1, '5': 3, '10': 'sumBurnedSats'},
  ],
};

/// Descriptor for `BlockInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockInfoDescriptor = $convert.base64Decode(
    'CglCbG9ja0luZm8SEgoEaGFzaBgBIAEoDFIEaGFzaBIbCglwcmV2X2hhc2gYAiABKAxSCHByZX'
    'ZIYXNoEhYKBmhlaWdodBgDIAEoBVIGaGVpZ2h0EhUKBm5fYml0cxgEIAEoDVIFbkJpdHMSHAoJ'
    'dGltZXN0YW1wGAUgASgDUgl0aW1lc3RhbXASGQoIaXNfZmluYWwYDiABKAhSB2lzRmluYWwSHQ'
    'oKYmxvY2tfc2l6ZRgGIAEoBFIJYmxvY2tTaXplEhcKB251bV90eHMYByABKARSBm51bVR4cxId'
    'CgpudW1faW5wdXRzGAggASgEUgludW1JbnB1dHMSHwoLbnVtX291dHB1dHMYCSABKARSCm51bU'
    '91dHB1dHMSJAoOc3VtX2lucHV0X3NhdHMYCiABKANSDHN1bUlucHV0U2F0cxI3ChhzdW1fY29p'
    'bmJhc2Vfb3V0cHV0X3NhdHMYCyABKANSFXN1bUNvaW5iYXNlT3V0cHV0U2F0cxIzChZzdW1fbm'
    '9ybWFsX291dHB1dF9zYXRzGAwgASgDUhNzdW1Ob3JtYWxPdXRwdXRTYXRzEiYKD3N1bV9idXJu'
    'ZWRfc2F0cxgNIAEoA1INc3VtQnVybmVkU2F0cw==');

@$core.Deprecated('Use txDescriptor instead')
const Tx$json = {
  '1': 'Tx',
  '2': [
    {'1': 'txid', '3': 1, '4': 1, '5': 12, '10': 'txid'},
    {'1': 'version', '3': 2, '4': 1, '5': 13, '10': 'version'},
    {
      '1': 'inputs',
      '3': 3,
      '4': 3,
      '5': 11,
      '6': '.chronik.TxInput',
      '10': 'inputs'
    },
    {
      '1': 'outputs',
      '3': 4,
      '4': 3,
      '5': 11,
      '6': '.chronik.TxOutput',
      '10': 'outputs'
    },
    {'1': 'lock_time', '3': 5, '4': 1, '5': 13, '10': 'lockTime'},
    {
      '1': 'block',
      '3': 8,
      '4': 1,
      '5': 11,
      '6': '.chronik.BlockMetadata',
      '10': 'block'
    },
    {'1': 'time_first_seen', '3': 9, '4': 1, '5': 3, '10': 'timeFirstSeen'},
    {'1': 'size', '3': 11, '4': 1, '5': 13, '10': 'size'},
    {'1': 'is_coinbase', '3': 12, '4': 1, '5': 8, '10': 'isCoinbase'},
    {
      '1': 'token_entries',
      '3': 13,
      '4': 3,
      '5': 11,
      '6': '.chronik.TokenEntry',
      '10': 'tokenEntries'
    },
    {
      '1': 'token_failed_parsings',
      '3': 14,
      '4': 3,
      '5': 11,
      '6': '.chronik.TokenFailedParsing',
      '10': 'tokenFailedParsings'
    },
    {
      '1': 'token_status',
      '3': 15,
      '4': 1,
      '5': 14,
      '6': '.chronik.TokenStatus',
      '10': 'tokenStatus'
    },
    {'1': 'is_final', '3': 16, '4': 1, '5': 8, '10': 'isFinal'},
  ],
};

/// Descriptor for `Tx`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List txDescriptor = $convert.base64Decode(
    'CgJUeBISCgR0eGlkGAEgASgMUgR0eGlkEhgKB3ZlcnNpb24YAiABKA1SB3ZlcnNpb24SKAoGaW'
    '5wdXRzGAMgAygLMhAuY2hyb25pay5UeElucHV0UgZpbnB1dHMSKwoHb3V0cHV0cxgEIAMoCzIR'
    'LmNocm9uaWsuVHhPdXRwdXRSB291dHB1dHMSGwoJbG9ja190aW1lGAUgASgNUghsb2NrVGltZR'
    'IsCgVibG9jaxgIIAEoCzIWLmNocm9uaWsuQmxvY2tNZXRhZGF0YVIFYmxvY2sSJgoPdGltZV9m'
    'aXJzdF9zZWVuGAkgASgDUg10aW1lRmlyc3RTZWVuEhIKBHNpemUYCyABKA1SBHNpemUSHwoLaX'
    'NfY29pbmJhc2UYDCABKAhSCmlzQ29pbmJhc2USOAoNdG9rZW5fZW50cmllcxgNIAMoCzITLmNo'
    'cm9uaWsuVG9rZW5FbnRyeVIMdG9rZW5FbnRyaWVzEk8KFXRva2VuX2ZhaWxlZF9wYXJzaW5ncx'
    'gOIAMoCzIbLmNocm9uaWsuVG9rZW5GYWlsZWRQYXJzaW5nUhN0b2tlbkZhaWxlZFBhcnNpbmdz'
    'EjcKDHRva2VuX3N0YXR1cxgPIAEoDjIULmNocm9uaWsuVG9rZW5TdGF0dXNSC3Rva2VuU3RhdH'
    'VzEhkKCGlzX2ZpbmFsGBAgASgIUgdpc0ZpbmFs');

@$core.Deprecated('Use scriptUtxoDescriptor instead')
const ScriptUtxo$json = {
  '1': 'ScriptUtxo',
  '2': [
    {
      '1': 'outpoint',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.OutPoint',
      '10': 'outpoint'
    },
    {'1': 'block_height', '3': 2, '4': 1, '5': 5, '10': 'blockHeight'},
    {'1': 'is_coinbase', '3': 3, '4': 1, '5': 8, '10': 'isCoinbase'},
    {'1': 'sats', '3': 5, '4': 1, '5': 3, '10': 'sats'},
    {'1': 'is_final', '3': 10, '4': 1, '5': 8, '10': 'isFinal'},
    {
      '1': 'token',
      '3': 11,
      '4': 1,
      '5': 11,
      '6': '.chronik.Token',
      '10': 'token'
    },
    {
      '1': 'plugins',
      '3': 12,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptUtxo.PluginsEntry',
      '10': 'plugins'
    },
  ],
  '3': [ScriptUtxo_PluginsEntry$json],
};

@$core.Deprecated('Use scriptUtxoDescriptor instead')
const ScriptUtxo_PluginsEntry$json = {
  '1': 'PluginsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {
      '1': 'value',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.PluginEntry',
      '10': 'value'
    },
  ],
  '7': {'7': true},
};

/// Descriptor for `ScriptUtxo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptUtxoDescriptor = $convert.base64Decode(
    'CgpTY3JpcHRVdHhvEi0KCG91dHBvaW50GAEgASgLMhEuY2hyb25pay5PdXRQb2ludFIIb3V0cG'
    '9pbnQSIQoMYmxvY2tfaGVpZ2h0GAIgASgFUgtibG9ja0hlaWdodBIfCgtpc19jb2luYmFzZRgD'
    'IAEoCFIKaXNDb2luYmFzZRISCgRzYXRzGAUgASgDUgRzYXRzEhkKCGlzX2ZpbmFsGAogASgIUg'
    'dpc0ZpbmFsEiQKBXRva2VuGAsgASgLMg4uY2hyb25pay5Ub2tlblIFdG9rZW4SOgoHcGx1Z2lu'
    'cxgMIAMoCzIgLmNocm9uaWsuU2NyaXB0VXR4by5QbHVnaW5zRW50cnlSB3BsdWdpbnMaUAoMUG'
    'x1Z2luc0VudHJ5EhAKA2tleRgBIAEoCVIDa2V5EioKBXZhbHVlGAIgASgLMhQuY2hyb25pay5Q'
    'bHVnaW5FbnRyeVIFdmFsdWU6AjgB');

@$core.Deprecated('Use utxoDescriptor instead')
const Utxo$json = {
  '1': 'Utxo',
  '2': [
    {
      '1': 'outpoint',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.OutPoint',
      '10': 'outpoint'
    },
    {'1': 'block_height', '3': 2, '4': 1, '5': 5, '10': 'blockHeight'},
    {'1': 'is_coinbase', '3': 3, '4': 1, '5': 8, '10': 'isCoinbase'},
    {'1': 'sats', '3': 4, '4': 1, '5': 3, '10': 'sats'},
    {'1': 'script', '3': 5, '4': 1, '5': 12, '10': 'script'},
    {'1': 'is_final', '3': 6, '4': 1, '5': 8, '10': 'isFinal'},
    {
      '1': 'token',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.chronik.Token',
      '10': 'token'
    },
    {
      '1': 'plugins',
      '3': 8,
      '4': 3,
      '5': 11,
      '6': '.chronik.Utxo.PluginsEntry',
      '10': 'plugins'
    },
  ],
  '3': [Utxo_PluginsEntry$json],
};

@$core.Deprecated('Use utxoDescriptor instead')
const Utxo_PluginsEntry$json = {
  '1': 'PluginsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {
      '1': 'value',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.PluginEntry',
      '10': 'value'
    },
  ],
  '7': {'7': true},
};

/// Descriptor for `Utxo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List utxoDescriptor = $convert.base64Decode(
    'CgRVdHhvEi0KCG91dHBvaW50GAEgASgLMhEuY2hyb25pay5PdXRQb2ludFIIb3V0cG9pbnQSIQ'
    'oMYmxvY2tfaGVpZ2h0GAIgASgFUgtibG9ja0hlaWdodBIfCgtpc19jb2luYmFzZRgDIAEoCFIK'
    'aXNDb2luYmFzZRISCgRzYXRzGAQgASgDUgRzYXRzEhYKBnNjcmlwdBgFIAEoDFIGc2NyaXB0Eh'
    'kKCGlzX2ZpbmFsGAYgASgIUgdpc0ZpbmFsEiQKBXRva2VuGAcgASgLMg4uY2hyb25pay5Ub2tl'
    'blIFdG9rZW4SNAoHcGx1Z2lucxgIIAMoCzIaLmNocm9uaWsuVXR4by5QbHVnaW5zRW50cnlSB3'
    'BsdWdpbnMaUAoMUGx1Z2luc0VudHJ5EhAKA2tleRgBIAEoCVIDa2V5EioKBXZhbHVlGAIgASgL'
    'MhQuY2hyb25pay5QbHVnaW5FbnRyeVIFdmFsdWU6AjgB');

@$core.Deprecated('Use outPointDescriptor instead')
const OutPoint$json = {
  '1': 'OutPoint',
  '2': [
    {'1': 'txid', '3': 1, '4': 1, '5': 12, '10': 'txid'},
    {'1': 'out_idx', '3': 2, '4': 1, '5': 13, '10': 'outIdx'},
  ],
};

/// Descriptor for `OutPoint`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List outPointDescriptor = $convert.base64Decode(
    'CghPdXRQb2ludBISCgR0eGlkGAEgASgMUgR0eGlkEhcKB291dF9pZHgYAiABKA1SBm91dElkeA'
    '==');

@$core.Deprecated('Use spentByDescriptor instead')
const SpentBy$json = {
  '1': 'SpentBy',
  '2': [
    {'1': 'txid', '3': 1, '4': 1, '5': 12, '10': 'txid'},
    {'1': 'input_idx', '3': 2, '4': 1, '5': 13, '10': 'inputIdx'},
  ],
};

/// Descriptor for `SpentBy`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List spentByDescriptor = $convert.base64Decode(
    'CgdTcGVudEJ5EhIKBHR4aWQYASABKAxSBHR4aWQSGwoJaW5wdXRfaWR4GAIgASgNUghpbnB1dE'
    'lkeA==');

@$core.Deprecated('Use txInputDescriptor instead')
const TxInput$json = {
  '1': 'TxInput',
  '2': [
    {
      '1': 'prev_out',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.OutPoint',
      '10': 'prevOut'
    },
    {'1': 'input_script', '3': 2, '4': 1, '5': 12, '10': 'inputScript'},
    {'1': 'output_script', '3': 3, '4': 1, '5': 12, '10': 'outputScript'},
    {'1': 'sats', '3': 4, '4': 1, '5': 3, '10': 'sats'},
    {'1': 'sequence_no', '3': 5, '4': 1, '5': 13, '10': 'sequenceNo'},
    {
      '1': 'token',
      '3': 8,
      '4': 1,
      '5': 11,
      '6': '.chronik.Token',
      '10': 'token'
    },
    {
      '1': 'plugins',
      '3': 9,
      '4': 3,
      '5': 11,
      '6': '.chronik.TxInput.PluginsEntry',
      '10': 'plugins'
    },
  ],
  '3': [TxInput_PluginsEntry$json],
};

@$core.Deprecated('Use txInputDescriptor instead')
const TxInput_PluginsEntry$json = {
  '1': 'PluginsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {
      '1': 'value',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.PluginEntry',
      '10': 'value'
    },
  ],
  '7': {'7': true},
};

/// Descriptor for `TxInput`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List txInputDescriptor = $convert.base64Decode(
    'CgdUeElucHV0EiwKCHByZXZfb3V0GAEgASgLMhEuY2hyb25pay5PdXRQb2ludFIHcHJldk91dB'
    'IhCgxpbnB1dF9zY3JpcHQYAiABKAxSC2lucHV0U2NyaXB0EiMKDW91dHB1dF9zY3JpcHQYAyAB'
    'KAxSDG91dHB1dFNjcmlwdBISCgRzYXRzGAQgASgDUgRzYXRzEh8KC3NlcXVlbmNlX25vGAUgAS'
    'gNUgpzZXF1ZW5jZU5vEiQKBXRva2VuGAggASgLMg4uY2hyb25pay5Ub2tlblIFdG9rZW4SNwoH'
    'cGx1Z2lucxgJIAMoCzIdLmNocm9uaWsuVHhJbnB1dC5QbHVnaW5zRW50cnlSB3BsdWdpbnMaUA'
    'oMUGx1Z2luc0VudHJ5EhAKA2tleRgBIAEoCVIDa2V5EioKBXZhbHVlGAIgASgLMhQuY2hyb25p'
    'ay5QbHVnaW5FbnRyeVIFdmFsdWU6AjgB');

@$core.Deprecated('Use txOutputDescriptor instead')
const TxOutput$json = {
  '1': 'TxOutput',
  '2': [
    {'1': 'sats', '3': 1, '4': 1, '5': 3, '10': 'sats'},
    {'1': 'output_script', '3': 2, '4': 1, '5': 12, '10': 'outputScript'},
    {
      '1': 'spent_by',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.chronik.SpentBy',
      '10': 'spentBy'
    },
    {
      '1': 'token',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.chronik.Token',
      '10': 'token'
    },
    {
      '1': 'plugins',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.chronik.TxOutput.PluginsEntry',
      '10': 'plugins'
    },
  ],
  '3': [TxOutput_PluginsEntry$json],
};

@$core.Deprecated('Use txOutputDescriptor instead')
const TxOutput_PluginsEntry$json = {
  '1': 'PluginsEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {
      '1': 'value',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.PluginEntry',
      '10': 'value'
    },
  ],
  '7': {'7': true},
};

/// Descriptor for `TxOutput`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List txOutputDescriptor = $convert.base64Decode(
    'CghUeE91dHB1dBISCgRzYXRzGAEgASgDUgRzYXRzEiMKDW91dHB1dF9zY3JpcHQYAiABKAxSDG'
    '91dHB1dFNjcmlwdBIrCghzcGVudF9ieRgEIAEoCzIQLmNocm9uaWsuU3BlbnRCeVIHc3BlbnRC'
    'eRIkCgV0b2tlbhgFIAEoCzIOLmNocm9uaWsuVG9rZW5SBXRva2VuEjgKB3BsdWdpbnMYBiADKA'
    'syHi5jaHJvbmlrLlR4T3V0cHV0LlBsdWdpbnNFbnRyeVIHcGx1Z2lucxpQCgxQbHVnaW5zRW50'
    'cnkSEAoDa2V5GAEgASgJUgNrZXkSKgoFdmFsdWUYAiABKAsyFC5jaHJvbmlrLlBsdWdpbkVudH'
    'J5UgV2YWx1ZToCOAE=');

@$core.Deprecated('Use blockMetadataDescriptor instead')
const BlockMetadata$json = {
  '1': 'BlockMetadata',
  '2': [
    {'1': 'height', '3': 1, '4': 1, '5': 5, '10': 'height'},
    {'1': 'hash', '3': 2, '4': 1, '5': 12, '10': 'hash'},
    {'1': 'timestamp', '3': 3, '4': 1, '5': 3, '10': 'timestamp'},
    {'1': 'is_final', '3': 4, '4': 1, '5': 8, '10': 'isFinal'},
  ],
};

/// Descriptor for `BlockMetadata`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List blockMetadataDescriptor = $convert.base64Decode(
    'Cg1CbG9ja01ldGFkYXRhEhYKBmhlaWdodBgBIAEoBVIGaGVpZ2h0EhIKBGhhc2gYAiABKAxSBG'
    'hhc2gSHAoJdGltZXN0YW1wGAMgASgDUgl0aW1lc3RhbXASGQoIaXNfZmluYWwYBCABKAhSB2lz'
    'RmluYWw=');

@$core.Deprecated('Use tokenTypeDescriptor instead')
const TokenType$json = {
  '1': 'TokenType',
  '2': [
    {
      '1': 'slp',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.chronik.SlpTokenType',
      '9': 0,
      '10': 'slp'
    },
    {
      '1': 'alp',
      '3': 2,
      '4': 1,
      '5': 14,
      '6': '.chronik.AlpTokenType',
      '9': 0,
      '10': 'alp'
    },
  ],
  '8': [
    {'1': 'token_type'},
  ],
};

/// Descriptor for `TokenType`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenTypeDescriptor = $convert.base64Decode(
    'CglUb2tlblR5cGUSKQoDc2xwGAEgASgOMhUuY2hyb25pay5TbHBUb2tlblR5cGVIAFIDc2xwEi'
    'kKA2FscBgCIAEoDjIVLmNocm9uaWsuQWxwVG9rZW5UeXBlSABSA2FscEIMCgp0b2tlbl90eXBl');

@$core.Deprecated('Use tokenInfoDescriptor instead')
const TokenInfo$json = {
  '1': 'TokenInfo',
  '2': [
    {'1': 'token_id', '3': 1, '4': 1, '5': 9, '10': 'tokenId'},
    {
      '1': 'token_type',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.TokenType',
      '10': 'tokenType'
    },
    {
      '1': 'genesis_info',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.chronik.GenesisInfo',
      '10': 'genesisInfo'
    },
    {
      '1': 'block',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.chronik.BlockMetadata',
      '10': 'block'
    },
    {'1': 'time_first_seen', '3': 5, '4': 1, '5': 3, '10': 'timeFirstSeen'},
  ],
};

/// Descriptor for `TokenInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenInfoDescriptor = $convert.base64Decode(
    'CglUb2tlbkluZm8SGQoIdG9rZW5faWQYASABKAlSB3Rva2VuSWQSMQoKdG9rZW5fdHlwZRgCIA'
    'EoCzISLmNocm9uaWsuVG9rZW5UeXBlUgl0b2tlblR5cGUSNwoMZ2VuZXNpc19pbmZvGAMgASgL'
    'MhQuY2hyb25pay5HZW5lc2lzSW5mb1ILZ2VuZXNpc0luZm8SLAoFYmxvY2sYBCABKAsyFi5jaH'
    'JvbmlrLkJsb2NrTWV0YWRhdGFSBWJsb2NrEiYKD3RpbWVfZmlyc3Rfc2VlbhgFIAEoA1INdGlt'
    'ZUZpcnN0U2Vlbg==');

@$core.Deprecated('Use tokenEntryDescriptor instead')
const TokenEntry$json = {
  '1': 'TokenEntry',
  '2': [
    {'1': 'token_id', '3': 1, '4': 1, '5': 9, '10': 'tokenId'},
    {
      '1': 'token_type',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.TokenType',
      '10': 'tokenType'
    },
    {
      '1': 'tx_type',
      '3': 3,
      '4': 1,
      '5': 14,
      '6': '.chronik.TokenTxType',
      '10': 'txType'
    },
    {'1': 'group_token_id', '3': 4, '4': 1, '5': 9, '10': 'groupTokenId'},
    {'1': 'is_invalid', '3': 5, '4': 1, '5': 8, '10': 'isInvalid'},
    {'1': 'burn_summary', '3': 6, '4': 1, '5': 9, '10': 'burnSummary'},
    {
      '1': 'failed_colorings',
      '3': 7,
      '4': 3,
      '5': 11,
      '6': '.chronik.TokenFailedColoring',
      '10': 'failedColorings'
    },
    {'1': 'actual_burn_atoms', '3': 8, '4': 1, '5': 9, '10': 'actualBurnAtoms'},
    {
      '1': 'intentional_burn_atoms',
      '3': 9,
      '4': 1,
      '5': 4,
      '10': 'intentionalBurnAtoms'
    },
    {
      '1': 'burns_mint_batons',
      '3': 10,
      '4': 1,
      '5': 8,
      '10': 'burnsMintBatons'
    },
  ],
};

/// Descriptor for `TokenEntry`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenEntryDescriptor = $convert.base64Decode(
    'CgpUb2tlbkVudHJ5EhkKCHRva2VuX2lkGAEgASgJUgd0b2tlbklkEjEKCnRva2VuX3R5cGUYAi'
    'ABKAsyEi5jaHJvbmlrLlRva2VuVHlwZVIJdG9rZW5UeXBlEi0KB3R4X3R5cGUYAyABKA4yFC5j'
    'aHJvbmlrLlRva2VuVHhUeXBlUgZ0eFR5cGUSJAoOZ3JvdXBfdG9rZW5faWQYBCABKAlSDGdyb3'
    'VwVG9rZW5JZBIdCgppc19pbnZhbGlkGAUgASgIUglpc0ludmFsaWQSIQoMYnVybl9zdW1tYXJ5'
    'GAYgASgJUgtidXJuU3VtbWFyeRJHChBmYWlsZWRfY29sb3JpbmdzGAcgAygLMhwuY2hyb25pay'
    '5Ub2tlbkZhaWxlZENvbG9yaW5nUg9mYWlsZWRDb2xvcmluZ3MSKgoRYWN0dWFsX2J1cm5fYXRv'
    'bXMYCCABKAlSD2FjdHVhbEJ1cm5BdG9tcxI0ChZpbnRlbnRpb25hbF9idXJuX2F0b21zGAkgAS'
    'gEUhRpbnRlbnRpb25hbEJ1cm5BdG9tcxIqChFidXJuc19taW50X2JhdG9ucxgKIAEoCFIPYnVy'
    'bnNNaW50QmF0b25z');

@$core.Deprecated('Use genesisInfoDescriptor instead')
const GenesisInfo$json = {
  '1': 'GenesisInfo',
  '2': [
    {'1': 'token_ticker', '3': 1, '4': 1, '5': 12, '10': 'tokenTicker'},
    {'1': 'token_name', '3': 2, '4': 1, '5': 12, '10': 'tokenName'},
    {'1': 'url', '3': 3, '4': 1, '5': 12, '10': 'url'},
    {'1': 'hash', '3': 4, '4': 1, '5': 12, '10': 'hash'},
    {
      '1': 'mint_vault_scripthash',
      '3': 5,
      '4': 1,
      '5': 12,
      '10': 'mintVaultScripthash'
    },
    {'1': 'data', '3': 6, '4': 1, '5': 12, '10': 'data'},
    {'1': 'auth_pubkey', '3': 7, '4': 1, '5': 12, '10': 'authPubkey'},
    {'1': 'decimals', '3': 8, '4': 1, '5': 13, '10': 'decimals'},
  ],
};

/// Descriptor for `GenesisInfo`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List genesisInfoDescriptor = $convert.base64Decode(
    'CgtHZW5lc2lzSW5mbxIhCgx0b2tlbl90aWNrZXIYASABKAxSC3Rva2VuVGlja2VyEh0KCnRva2'
    'VuX25hbWUYAiABKAxSCXRva2VuTmFtZRIQCgN1cmwYAyABKAxSA3VybBISCgRoYXNoGAQgASgM'
    'UgRoYXNoEjIKFW1pbnRfdmF1bHRfc2NyaXB0aGFzaBgFIAEoDFITbWludFZhdWx0U2NyaXB0aG'
    'FzaBISCgRkYXRhGAYgASgMUgRkYXRhEh8KC2F1dGhfcHVia2V5GAcgASgMUgphdXRoUHVia2V5'
    'EhoKCGRlY2ltYWxzGAggASgNUghkZWNpbWFscw==');

@$core.Deprecated('Use tokenDescriptor instead')
const Token$json = {
  '1': 'Token',
  '2': [
    {'1': 'token_id', '3': 1, '4': 1, '5': 9, '10': 'tokenId'},
    {
      '1': 'token_type',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.TokenType',
      '10': 'tokenType'
    },
    {'1': 'entry_idx', '3': 3, '4': 1, '5': 5, '10': 'entryIdx'},
    {'1': 'atoms', '3': 4, '4': 1, '5': 4, '10': 'atoms'},
    {'1': 'is_mint_baton', '3': 5, '4': 1, '5': 8, '10': 'isMintBaton'},
  ],
};

/// Descriptor for `Token`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenDescriptor = $convert.base64Decode(
    'CgVUb2tlbhIZCgh0b2tlbl9pZBgBIAEoCVIHdG9rZW5JZBIxCgp0b2tlbl90eXBlGAIgASgLMh'
    'IuY2hyb25pay5Ub2tlblR5cGVSCXRva2VuVHlwZRIbCgllbnRyeV9pZHgYAyABKAVSCGVudHJ5'
    'SWR4EhQKBWF0b21zGAQgASgEUgVhdG9tcxIiCg1pc19taW50X2JhdG9uGAUgASgIUgtpc01pbn'
    'RCYXRvbg==');

@$core.Deprecated('Use tokenFailedParsingDescriptor instead')
const TokenFailedParsing$json = {
  '1': 'TokenFailedParsing',
  '2': [
    {'1': 'pushdata_idx', '3': 1, '4': 1, '5': 5, '10': 'pushdataIdx'},
    {'1': 'bytes', '3': 2, '4': 1, '5': 12, '10': 'bytes'},
    {'1': 'error', '3': 3, '4': 1, '5': 9, '10': 'error'},
  ],
};

/// Descriptor for `TokenFailedParsing`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenFailedParsingDescriptor = $convert.base64Decode(
    'ChJUb2tlbkZhaWxlZFBhcnNpbmcSIQoMcHVzaGRhdGFfaWR4GAEgASgFUgtwdXNoZGF0YUlkeB'
    'IUCgVieXRlcxgCIAEoDFIFYnl0ZXMSFAoFZXJyb3IYAyABKAlSBWVycm9y');

@$core.Deprecated('Use tokenFailedColoringDescriptor instead')
const TokenFailedColoring$json = {
  '1': 'TokenFailedColoring',
  '2': [
    {'1': 'pushdata_idx', '3': 1, '4': 1, '5': 5, '10': 'pushdataIdx'},
    {'1': 'error', '3': 3, '4': 1, '5': 9, '10': 'error'},
  ],
};

/// Descriptor for `TokenFailedColoring`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List tokenFailedColoringDescriptor = $convert.base64Decode(
    'ChNUb2tlbkZhaWxlZENvbG9yaW5nEiEKDHB1c2hkYXRhX2lkeBgBIAEoBVILcHVzaGRhdGFJZH'
    'gSFAoFZXJyb3IYAyABKAlSBWVycm9y');

@$core.Deprecated('Use pluginEntryDescriptor instead')
const PluginEntry$json = {
  '1': 'PluginEntry',
  '2': [
    {'1': 'groups', '3': 1, '4': 3, '5': 12, '10': 'groups'},
    {'1': 'data', '3': 2, '4': 3, '5': 12, '10': 'data'},
  ],
};

/// Descriptor for `PluginEntry`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List pluginEntryDescriptor = $convert.base64Decode(
    'CgtQbHVnaW5FbnRyeRIWCgZncm91cHMYASADKAxSBmdyb3VwcxISCgRkYXRhGAIgAygMUgRkYX'
    'Rh');

@$core.Deprecated('Use pluginGroupDescriptor instead')
const PluginGroup$json = {
  '1': 'PluginGroup',
  '2': [
    {'1': 'group', '3': 1, '4': 1, '5': 12, '10': 'group'},
  ],
};

/// Descriptor for `PluginGroup`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List pluginGroupDescriptor =
    $convert.base64Decode('CgtQbHVnaW5Hcm91cBIUCgVncm91cBgBIAEoDFIFZ3JvdXA=');

@$core.Deprecated('Use pluginGroupsDescriptor instead')
const PluginGroups$json = {
  '1': 'PluginGroups',
  '2': [
    {
      '1': 'groups',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.PluginGroup',
      '10': 'groups'
    },
    {'1': 'next_start', '3': 2, '4': 1, '5': 12, '10': 'nextStart'},
  ],
};

/// Descriptor for `PluginGroups`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List pluginGroupsDescriptor = $convert.base64Decode(
    'CgxQbHVnaW5Hcm91cHMSLAoGZ3JvdXBzGAEgAygLMhQuY2hyb25pay5QbHVnaW5Hcm91cFIGZ3'
    'JvdXBzEh0KCm5leHRfc3RhcnQYAiABKAxSCW5leHRTdGFydA==');

@$core.Deprecated('Use txHistoryPageDescriptor instead')
const TxHistoryPage$json = {
  '1': 'TxHistoryPage',
  '2': [
    {'1': 'txs', '3': 1, '4': 3, '5': 11, '6': '.chronik.Tx', '10': 'txs'},
    {'1': 'num_pages', '3': 2, '4': 1, '5': 13, '10': 'numPages'},
    {'1': 'num_txs', '3': 3, '4': 1, '5': 13, '10': 'numTxs'},
  ],
};

/// Descriptor for `TxHistoryPage`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List txHistoryPageDescriptor = $convert.base64Decode(
    'Cg1UeEhpc3RvcnlQYWdlEh0KA3R4cxgBIAMoCzILLmNocm9uaWsuVHhSA3R4cxIbCgludW1fcG'
    'FnZXMYAiABKA1SCG51bVBhZ2VzEhcKB251bV90eHMYAyABKA1SBm51bVR4cw==');

@$core.Deprecated('Use scriptUtxosDescriptor instead')
const ScriptUtxos$json = {
  '1': 'ScriptUtxos',
  '2': [
    {'1': 'script', '3': 1, '4': 1, '5': 12, '10': 'script'},
    {
      '1': 'utxos',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptUtxo',
      '10': 'utxos'
    },
  ],
};

/// Descriptor for `ScriptUtxos`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptUtxosDescriptor = $convert.base64Decode(
    'CgtTY3JpcHRVdHhvcxIWCgZzY3JpcHQYASABKAxSBnNjcmlwdBIpCgV1dHhvcxgCIAMoCzITLm'
    'Nocm9uaWsuU2NyaXB0VXR4b1IFdXR4b3M=');

@$core.Deprecated('Use scriptRefDescriptor instead')
const ScriptRef$json = {
  '1': 'ScriptRef',
  '2': [
    {'1': 'script_type', '3': 1, '4': 1, '5': 9, '10': 'scriptType'},
    {'1': 'payload', '3': 2, '4': 1, '5': 12, '10': 'payload'},
  ],
};

/// Descriptor for `ScriptRef`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptRefDescriptor = $convert.base64Decode(
    'CglTY3JpcHRSZWYSHwoLc2NyaXB0X3R5cGUYASABKAlSCnNjcmlwdFR5cGUSGAoHcGF5bG9hZB'
    'gCIAEoDFIHcGF5bG9hZA==');

@$core.Deprecated('Use scriptBatchUtxosParamsDescriptor instead')
const ScriptBatchUtxosParams$json = {
  '1': 'ScriptBatchUtxosParams',
  '2': [
    {
      '1': 'scripts',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptRef',
      '10': 'scripts'
    },
  ],
};

/// Descriptor for `ScriptBatchUtxosParams`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchUtxosParamsDescriptor =
    $convert.base64Decode(
        'ChZTY3JpcHRCYXRjaFV0eG9zUGFyYW1zEiwKB3NjcmlwdHMYASADKAsyEi5jaHJvbmlrLlNjcm'
        'lwdFJlZlIHc2NyaXB0cw==');

@$core.Deprecated('Use scriptBatchUtxosRequestDescriptor instead')
const ScriptBatchUtxosRequest$json = {
  '1': 'ScriptBatchUtxosRequest',
  '2': [
    {
      '1': 'params',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.ScriptBatchUtxosParams',
      '10': 'params'
    },
  ],
};

/// Descriptor for `ScriptBatchUtxosRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchUtxosRequestDescriptor =
    $convert.base64Decode(
        'ChdTY3JpcHRCYXRjaFV0eG9zUmVxdWVzdBI3CgZwYXJhbXMYASABKAsyHy5jaHJvbmlrLlNjcm'
        'lwdEJhdGNoVXR4b3NQYXJhbXNSBnBhcmFtcw==');

@$core.Deprecated('Use scriptBatchUtxosRowDescriptor instead')
const ScriptBatchUtxosRow$json = {
  '1': 'ScriptBatchUtxosRow',
  '2': [
    {
      '1': 'script',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.ScriptRef',
      '10': 'script'
    },
    {
      '1': 'utxos',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.ScriptUtxos',
      '10': 'utxos'
    },
  ],
};

/// Descriptor for `ScriptBatchUtxosRow`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchUtxosRowDescriptor = $convert.base64Decode(
    'ChNTY3JpcHRCYXRjaFV0eG9zUm93EioKBnNjcmlwdBgBIAEoCzISLmNocm9uaWsuU2NyaXB0Um'
    'VmUgZzY3JpcHQSKgoFdXR4b3MYAiABKAsyFC5jaHJvbmlrLlNjcmlwdFV0eG9zUgV1dHhvcw==');

@$core.Deprecated('Use scriptBatchUtxosResponseDescriptor instead')
const ScriptBatchUtxosResponse$json = {
  '1': 'ScriptBatchUtxosResponse',
  '2': [
    {
      '1': 'rows',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptBatchUtxosRow',
      '10': 'rows'
    },
  ],
};

/// Descriptor for `ScriptBatchUtxosResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchUtxosResponseDescriptor =
    $convert.base64Decode(
        'ChhTY3JpcHRCYXRjaFV0eG9zUmVzcG9uc2USMAoEcm93cxgBIAMoCzIcLmNocm9uaWsuU2NyaX'
        'B0QmF0Y2hVdHhvc1Jvd1IEcm93cw==');

@$core.Deprecated('Use scriptBatchSummaryParamsDescriptor instead')
const ScriptBatchSummaryParams$json = {
  '1': 'ScriptBatchSummaryParams',
  '2': [
    {
      '1': 'scripts',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptRef',
      '10': 'scripts'
    },
  ],
};

/// Descriptor for `ScriptBatchSummaryParams`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchSummaryParamsDescriptor =
    $convert.base64Decode(
        'ChhTY3JpcHRCYXRjaFN1bW1hcnlQYXJhbXMSLAoHc2NyaXB0cxgBIAMoCzISLmNocm9uaWsuU2'
        'NyaXB0UmVmUgdzY3JpcHRz');

@$core.Deprecated('Use scriptBatchSummaryRequestDescriptor instead')
const ScriptBatchSummaryRequest$json = {
  '1': 'ScriptBatchSummaryRequest',
  '2': [
    {
      '1': 'params',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.ScriptBatchSummaryParams',
      '10': 'params'
    },
  ],
};

/// Descriptor for `ScriptBatchSummaryRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchSummaryRequestDescriptor =
    $convert.base64Decode(
        'ChlTY3JpcHRCYXRjaFN1bW1hcnlSZXF1ZXN0EjkKBnBhcmFtcxgBIAEoCzIhLmNocm9uaWsuU2'
        'NyaXB0QmF0Y2hTdW1tYXJ5UGFyYW1zUgZwYXJhbXM=');

@$core.Deprecated('Use scriptBatchSummaryRowDescriptor instead')
const ScriptBatchSummaryRow$json = {
  '1': 'ScriptBatchSummaryRow',
  '2': [
    {
      '1': 'script',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.ScriptRef',
      '10': 'script'
    },
    {'1': 'num_txs', '3': 2, '4': 1, '5': 13, '10': 'numTxs'},
    {'1': 'num_utxos', '3': 3, '4': 1, '5': 13, '10': 'numUtxos'},
    {
      '1': 'latest_tx',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.chronik.Tx',
      '10': 'latestTx'
    },
  ],
};

/// Descriptor for `ScriptBatchSummaryRow`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchSummaryRowDescriptor = $convert.base64Decode(
    'ChVTY3JpcHRCYXRjaFN1bW1hcnlSb3cSKgoGc2NyaXB0GAEgASgLMhIuY2hyb25pay5TY3JpcH'
    'RSZWZSBnNjcmlwdBIXCgdudW1fdHhzGAIgASgNUgZudW1UeHMSGwoJbnVtX3V0eG9zGAMgASgN'
    'UghudW1VdHhvcxIoCglsYXRlc3RfdHgYBCABKAsyCy5jaHJvbmlrLlR4UghsYXRlc3RUeA==');

@$core.Deprecated('Use scriptBatchSummaryResponseDescriptor instead')
const ScriptBatchSummaryResponse$json = {
  '1': 'ScriptBatchSummaryResponse',
  '2': [
    {
      '1': 'rows',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.ScriptBatchSummaryRow',
      '10': 'rows'
    },
  ],
};

/// Descriptor for `ScriptBatchSummaryResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List scriptBatchSummaryResponseDescriptor =
    $convert.base64Decode(
        'ChpTY3JpcHRCYXRjaFN1bW1hcnlSZXNwb25zZRIyCgRyb3dzGAEgAygLMh4uY2hyb25pay5TY3'
        'JpcHRCYXRjaFN1bW1hcnlSb3dSBHJvd3M=');

@$core.Deprecated('Use utxosDescriptor instead')
const Utxos$json = {
  '1': 'Utxos',
  '2': [
    {
      '1': 'utxos',
      '3': 1,
      '4': 3,
      '5': 11,
      '6': '.chronik.Utxo',
      '10': 'utxos'
    },
  ],
};

/// Descriptor for `Utxos`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List utxosDescriptor = $convert.base64Decode(
    'CgVVdHhvcxIjCgV1dHhvcxgBIAMoCzINLmNocm9uaWsuVXR4b1IFdXR4b3M=');

@$core.Deprecated('Use broadcastTxRequestDescriptor instead')
const BroadcastTxRequest$json = {
  '1': 'BroadcastTxRequest',
  '2': [
    {'1': 'raw_tx', '3': 1, '4': 1, '5': 12, '10': 'rawTx'},
    {'1': 'skip_token_checks', '3': 2, '4': 1, '5': 8, '10': 'skipTokenChecks'},
    {
      '1': 'finalization_timeout_secs',
      '3': 3,
      '4': 1,
      '5': 4,
      '10': 'finalizationTimeoutSecs'
    },
  ],
};

/// Descriptor for `BroadcastTxRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List broadcastTxRequestDescriptor = $convert.base64Decode(
    'ChJCcm9hZGNhc3RUeFJlcXVlc3QSFQoGcmF3X3R4GAEgASgMUgVyYXdUeBIqChFza2lwX3Rva2'
    'VuX2NoZWNrcxgCIAEoCFIPc2tpcFRva2VuQ2hlY2tzEjoKGWZpbmFsaXphdGlvbl90aW1lb3V0'
    'X3NlY3MYAyABKARSF2ZpbmFsaXphdGlvblRpbWVvdXRTZWNz');

@$core.Deprecated('Use broadcastTxResponseDescriptor instead')
const BroadcastTxResponse$json = {
  '1': 'BroadcastTxResponse',
  '2': [
    {'1': 'txid', '3': 1, '4': 1, '5': 12, '10': 'txid'},
  ],
};

/// Descriptor for `BroadcastTxResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List broadcastTxResponseDescriptor = $convert
    .base64Decode('ChNCcm9hZGNhc3RUeFJlc3BvbnNlEhIKBHR4aWQYASABKAxSBHR4aWQ=');

@$core.Deprecated('Use broadcastTxsRequestDescriptor instead')
const BroadcastTxsRequest$json = {
  '1': 'BroadcastTxsRequest',
  '2': [
    {'1': 'raw_txs', '3': 1, '4': 3, '5': 12, '10': 'rawTxs'},
    {'1': 'skip_token_checks', '3': 2, '4': 1, '5': 8, '10': 'skipTokenChecks'},
    {
      '1': 'finalization_timeout_secs',
      '3': 3,
      '4': 1,
      '5': 4,
      '10': 'finalizationTimeoutSecs'
    },
  ],
};

/// Descriptor for `BroadcastTxsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List broadcastTxsRequestDescriptor = $convert.base64Decode(
    'ChNCcm9hZGNhc3RUeHNSZXF1ZXN0EhcKB3Jhd190eHMYASADKAxSBnJhd1R4cxIqChFza2lwX3'
    'Rva2VuX2NoZWNrcxgCIAEoCFIPc2tpcFRva2VuQ2hlY2tzEjoKGWZpbmFsaXphdGlvbl90aW1l'
    'b3V0X3NlY3MYAyABKARSF2ZpbmFsaXphdGlvblRpbWVvdXRTZWNz');

@$core.Deprecated('Use broadcastTxsResponseDescriptor instead')
const BroadcastTxsResponse$json = {
  '1': 'BroadcastTxsResponse',
  '2': [
    {'1': 'txids', '3': 1, '4': 3, '5': 12, '10': 'txids'},
  ],
};

/// Descriptor for `BroadcastTxsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List broadcastTxsResponseDescriptor =
    $convert.base64Decode(
        'ChRCcm9hZGNhc3RUeHNSZXNwb25zZRIUCgV0eGlkcxgBIAMoDFIFdHhpZHM=');

@$core.Deprecated('Use rawTxDescriptor instead')
const RawTx$json = {
  '1': 'RawTx',
  '2': [
    {'1': 'raw_tx', '3': 1, '4': 1, '5': 12, '10': 'rawTx'},
  ],
};

/// Descriptor for `RawTx`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List rawTxDescriptor =
    $convert.base64Decode('CgVSYXdUeBIVCgZyYXdfdHgYASABKAxSBXJhd1R4');

@$core.Deprecated('Use wsSubDescriptor instead')
const WsSub$json = {
  '1': 'WsSub',
  '2': [
    {'1': 'is_unsub', '3': 1, '4': 1, '5': 8, '10': 'isUnsub'},
    {
      '1': 'blocks',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubBlocks',
      '9': 0,
      '10': 'blocks'
    },
    {
      '1': 'txs',
      '3': 8,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubTxs',
      '9': 0,
      '10': 'txs'
    },
    {
      '1': 'script',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubScript',
      '9': 0,
      '10': 'script'
    },
    {
      '1': 'token_id',
      '3': 4,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubTokenId',
      '9': 0,
      '10': 'tokenId'
    },
    {
      '1': 'lokad_id',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubLokadId',
      '9': 0,
      '10': 'lokadId'
    },
    {
      '1': 'plugin',
      '3': 6,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsPlugin',
      '9': 0,
      '10': 'plugin'
    },
    {
      '1': 'txid',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.chronik.WsSubTxId',
      '9': 0,
      '10': 'txid'
    },
  ],
  '8': [
    {'1': 'sub_type'},
  ],
};

/// Descriptor for `WsSub`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubDescriptor = $convert.base64Decode(
    'CgVXc1N1YhIZCghpc191bnN1YhgBIAEoCFIHaXNVbnN1YhIuCgZibG9ja3MYAiABKAsyFC5jaH'
    'JvbmlrLldzU3ViQmxvY2tzSABSBmJsb2NrcxIlCgN0eHMYCCABKAsyES5jaHJvbmlrLldzU3Vi'
    'VHhzSABSA3R4cxIuCgZzY3JpcHQYAyABKAsyFC5jaHJvbmlrLldzU3ViU2NyaXB0SABSBnNjcm'
    'lwdBIyCgh0b2tlbl9pZBgEIAEoCzIVLmNocm9uaWsuV3NTdWJUb2tlbklkSABSB3Rva2VuSWQS'
    'MgoIbG9rYWRfaWQYBSABKAsyFS5jaHJvbmlrLldzU3ViTG9rYWRJZEgAUgdsb2thZElkEisKBn'
    'BsdWdpbhgGIAEoCzIRLmNocm9uaWsuV3NQbHVnaW5IAFIGcGx1Z2luEigKBHR4aWQYByABKAsy'
    'Ei5jaHJvbmlrLldzU3ViVHhJZEgAUgR0eGlkQgoKCHN1Yl90eXBl');

@$core.Deprecated('Use wsSubBlocksDescriptor instead')
const WsSubBlocks$json = {
  '1': 'WsSubBlocks',
};

/// Descriptor for `WsSubBlocks`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubBlocksDescriptor =
    $convert.base64Decode('CgtXc1N1YkJsb2Nrcw==');

@$core.Deprecated('Use wsSubTxsDescriptor instead')
const WsSubTxs$json = {
  '1': 'WsSubTxs',
};

/// Descriptor for `WsSubTxs`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubTxsDescriptor =
    $convert.base64Decode('CghXc1N1YlR4cw==');

@$core.Deprecated('Use wsSubScriptDescriptor instead')
const WsSubScript$json = {
  '1': 'WsSubScript',
  '2': [
    {'1': 'script_type', '3': 1, '4': 1, '5': 9, '10': 'scriptType'},
    {'1': 'payload', '3': 2, '4': 1, '5': 12, '10': 'payload'},
  ],
};

/// Descriptor for `WsSubScript`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubScriptDescriptor = $convert.base64Decode(
    'CgtXc1N1YlNjcmlwdBIfCgtzY3JpcHRfdHlwZRgBIAEoCVIKc2NyaXB0VHlwZRIYCgdwYXlsb2'
    'FkGAIgASgMUgdwYXlsb2Fk');

@$core.Deprecated('Use wsSubTokenIdDescriptor instead')
const WsSubTokenId$json = {
  '1': 'WsSubTokenId',
  '2': [
    {'1': 'token_id', '3': 1, '4': 1, '5': 9, '10': 'tokenId'},
  ],
};

/// Descriptor for `WsSubTokenId`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubTokenIdDescriptor = $convert
    .base64Decode('CgxXc1N1YlRva2VuSWQSGQoIdG9rZW5faWQYASABKAlSB3Rva2VuSWQ=');

@$core.Deprecated('Use wsSubLokadIdDescriptor instead')
const WsSubLokadId$json = {
  '1': 'WsSubLokadId',
  '2': [
    {'1': 'lokad_id', '3': 1, '4': 1, '5': 12, '10': 'lokadId'},
  ],
};

/// Descriptor for `WsSubLokadId`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubLokadIdDescriptor = $convert
    .base64Decode('CgxXc1N1Ykxva2FkSWQSGQoIbG9rYWRfaWQYASABKAxSB2xva2FkSWQ=');

@$core.Deprecated('Use wsPluginDescriptor instead')
const WsPlugin$json = {
  '1': 'WsPlugin',
  '2': [
    {'1': 'plugin_name', '3': 1, '4': 1, '5': 9, '10': 'pluginName'},
    {'1': 'group', '3': 2, '4': 1, '5': 12, '10': 'group'},
  ],
};

/// Descriptor for `WsPlugin`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsPluginDescriptor = $convert.base64Decode(
    'CghXc1BsdWdpbhIfCgtwbHVnaW5fbmFtZRgBIAEoCVIKcGx1Z2luTmFtZRIUCgVncm91cBgCIA'
    'EoDFIFZ3JvdXA=');

@$core.Deprecated('Use wsSubTxIdDescriptor instead')
const WsSubTxId$json = {
  '1': 'WsSubTxId',
  '2': [
    {'1': 'txid', '3': 1, '4': 1, '5': 9, '10': 'txid'},
  ],
};

/// Descriptor for `WsSubTxId`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsSubTxIdDescriptor =
    $convert.base64Decode('CglXc1N1YlR4SWQSEgoEdHhpZBgBIAEoCVIEdHhpZA==');

@$core.Deprecated('Use wsMsgDescriptor instead')
const WsMsg$json = {
  '1': 'WsMsg',
  '2': [
    {
      '1': 'error',
      '3': 1,
      '4': 1,
      '5': 11,
      '6': '.chronik.Error',
      '9': 0,
      '10': 'error'
    },
    {
      '1': 'block',
      '3': 2,
      '4': 1,
      '5': 11,
      '6': '.chronik.MsgBlock',
      '9': 0,
      '10': 'block'
    },
    {
      '1': 'tx',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.chronik.MsgTx',
      '9': 0,
      '10': 'tx'
    },
  ],
  '8': [
    {'1': 'msg_type'},
  ],
};

/// Descriptor for `WsMsg`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wsMsgDescriptor = $convert.base64Decode(
    'CgVXc01zZxImCgVlcnJvchgBIAEoCzIOLmNocm9uaWsuRXJyb3JIAFIFZXJyb3ISKQoFYmxvY2'
    'sYAiABKAsyES5jaHJvbmlrLk1zZ0Jsb2NrSABSBWJsb2NrEiAKAnR4GAMgASgLMg4uY2hyb25p'
    'ay5Nc2dUeEgAUgJ0eEIKCghtc2dfdHlwZQ==');

@$core.Deprecated('Use coinbaseDataDescriptor instead')
const CoinbaseData$json = {
  '1': 'CoinbaseData',
  '2': [
    {
      '1': 'coinbase_scriptsig',
      '3': 1,
      '4': 1,
      '5': 12,
      '10': 'coinbaseScriptsig'
    },
    {
      '1': 'coinbase_outputs',
      '3': 2,
      '4': 3,
      '5': 11,
      '6': '.chronik.TxOutput',
      '10': 'coinbaseOutputs'
    },
  ],
};

/// Descriptor for `CoinbaseData`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List coinbaseDataDescriptor = $convert.base64Decode(
    'CgxDb2luYmFzZURhdGESLQoSY29pbmJhc2Vfc2NyaXB0c2lnGAEgASgMUhFjb2luYmFzZVNjcm'
    'lwdHNpZxI8ChBjb2luYmFzZV9vdXRwdXRzGAIgAygLMhEuY2hyb25pay5UeE91dHB1dFIPY29p'
    'bmJhc2VPdXRwdXRz');

@$core.Deprecated('Use msgBlockDescriptor instead')
const MsgBlock$json = {
  '1': 'MsgBlock',
  '2': [
    {
      '1': 'msg_type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.chronik.BlockMsgType',
      '10': 'msgType'
    },
    {'1': 'block_hash', '3': 2, '4': 1, '5': 12, '10': 'blockHash'},
    {'1': 'block_height', '3': 3, '4': 1, '5': 5, '10': 'blockHeight'},
    {'1': 'block_timestamp', '3': 4, '4': 1, '5': 3, '10': 'blockTimestamp'},
    {
      '1': 'coinbase_data',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.chronik.CoinbaseData',
      '10': 'coinbaseData'
    },
  ],
};

/// Descriptor for `MsgBlock`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List msgBlockDescriptor = $convert.base64Decode(
    'CghNc2dCbG9jaxIwCghtc2dfdHlwZRgBIAEoDjIVLmNocm9uaWsuQmxvY2tNc2dUeXBlUgdtc2'
    'dUeXBlEh0KCmJsb2NrX2hhc2gYAiABKAxSCWJsb2NrSGFzaBIhCgxibG9ja19oZWlnaHQYAyAB'
    'KAVSC2Jsb2NrSGVpZ2h0EicKD2Jsb2NrX3RpbWVzdGFtcBgEIAEoA1IOYmxvY2tUaW1lc3RhbX'
    'ASOgoNY29pbmJhc2VfZGF0YRgFIAEoCzIVLmNocm9uaWsuQ29pbmJhc2VEYXRhUgxjb2luYmFz'
    'ZURhdGE=');

@$core.Deprecated('Use txFinalizationReasonDescriptor instead')
const TxFinalizationReason$json = {
  '1': 'TxFinalizationReason',
  '2': [
    {
      '1': 'finalization_type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.chronik.TxFinalizationReasonType',
      '10': 'finalizationType'
    },
  ],
};

/// Descriptor for `TxFinalizationReason`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List txFinalizationReasonDescriptor = $convert.base64Decode(
    'ChRUeEZpbmFsaXphdGlvblJlYXNvbhJOChFmaW5hbGl6YXRpb25fdHlwZRgBIAEoDjIhLmNocm'
    '9uaWsuVHhGaW5hbGl6YXRpb25SZWFzb25UeXBlUhBmaW5hbGl6YXRpb25UeXBl');

@$core.Deprecated('Use msgTxDescriptor instead')
const MsgTx$json = {
  '1': 'MsgTx',
  '2': [
    {
      '1': 'msg_type',
      '3': 1,
      '4': 1,
      '5': 14,
      '6': '.chronik.TxMsgType',
      '10': 'msgType'
    },
    {'1': 'txid', '3': 2, '4': 1, '5': 12, '10': 'txid'},
    {
      '1': 'finalization_reason',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.chronik.TxFinalizationReason',
      '10': 'finalizationReason'
    },
  ],
};

/// Descriptor for `MsgTx`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List msgTxDescriptor = $convert.base64Decode(
    'CgVNc2dUeBItCghtc2dfdHlwZRgBIAEoDjISLmNocm9uaWsuVHhNc2dUeXBlUgdtc2dUeXBlEh'
    'IKBHR4aWQYAiABKAxSBHR4aWQSTgoTZmluYWxpemF0aW9uX3JlYXNvbhgDIAEoCzIdLmNocm9u'
    'aWsuVHhGaW5hbGl6YXRpb25SZWFzb25SEmZpbmFsaXphdGlvblJlYXNvbg==');

@$core.Deprecated('Use emptyDescriptor instead')
const Empty$json = {
  '1': 'Empty',
};

/// Descriptor for `Empty`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List emptyDescriptor =
    $convert.base64Decode('CgVFbXB0eQ==');

@$core.Deprecated('Use errorDescriptor instead')
const Error$json = {
  '1': 'Error',
  '2': [
    {'1': 'msg', '3': 2, '4': 1, '5': 9, '10': 'msg'},
  ],
};

/// Descriptor for `Error`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List errorDescriptor =
    $convert.base64Decode('CgVFcnJvchIQCgNtc2cYAiABKAlSA21zZw==');
