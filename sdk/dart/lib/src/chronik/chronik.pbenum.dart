// This is a generated file - do not edit.
//
// Generated from chronik.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

/// Status of a token tx
class TokenStatus extends $pb.ProtobufEnum {
  /// Tx involves no tokens whatsover, i.e. neither any burns nor any failed
  /// parsing/coloring or any tokens being created / moved.
  static const TokenStatus TOKEN_STATUS_NON_TOKEN =
      TokenStatus._(0, _omitEnumNames ? '' : 'TOKEN_STATUS_NON_TOKEN');

  /// Tx involves tokens but no unintentional burns or failed parsings/colorings
  static const TokenStatus TOKEN_STATUS_NORMAL =
      TokenStatus._(1, _omitEnumNames ? '' : 'TOKEN_STATUS_NORMAL');

  /// Tx involves tokens but contains unintentional burns or failed parsings/colorings
  static const TokenStatus TOKEN_STATUS_NOT_NORMAL =
      TokenStatus._(2, _omitEnumNames ? '' : 'TOKEN_STATUS_NOT_NORMAL');

  static const $core.List<TokenStatus> values = <TokenStatus>[
    TOKEN_STATUS_NON_TOKEN,
    TOKEN_STATUS_NORMAL,
    TOKEN_STATUS_NOT_NORMAL,
  ];

  static final $core.List<TokenStatus?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 2);
  static TokenStatus? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const TokenStatus._(super.value, super.name);
}

/// ALP token type
class AlpTokenType extends $pb.ProtobufEnum {
  /// Standard ALP token type
  static const AlpTokenType ALP_TOKEN_TYPE_STANDARD =
      AlpTokenType._(0, _omitEnumNames ? '' : 'ALP_TOKEN_TYPE_STANDARD');

  static const $core.List<AlpTokenType> values = <AlpTokenType>[
    ALP_TOKEN_TYPE_STANDARD,
  ];

  static final $core.List<AlpTokenType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 0);
  static AlpTokenType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const AlpTokenType._(super.value, super.name);
}

/// SLP token type
class SlpTokenType extends $pb.ProtobufEnum {
  /// Unknown "0" token type
  static const SlpTokenType SLP_TOKEN_TYPE_NONE =
      SlpTokenType._(0, _omitEnumNames ? '' : 'SLP_TOKEN_TYPE_NONE');

  /// SLP V1 token type
  static const SlpTokenType SLP_TOKEN_TYPE_FUNGIBLE =
      SlpTokenType._(1, _omitEnumNames ? '' : 'SLP_TOKEN_TYPE_FUNGIBLE');

  /// SLP V2 mint vault token type
  static const SlpTokenType SLP_TOKEN_TYPE_MINT_VAULT =
      SlpTokenType._(2, _omitEnumNames ? '' : 'SLP_TOKEN_TYPE_MINT_VAULT');

  /// NFT1 group token type
  static const SlpTokenType SLP_TOKEN_TYPE_NFT1_GROUP =
      SlpTokenType._(129, _omitEnumNames ? '' : 'SLP_TOKEN_TYPE_NFT1_GROUP');

  /// NFT1 child token type
  static const SlpTokenType SLP_TOKEN_TYPE_NFT1_CHILD =
      SlpTokenType._(65, _omitEnumNames ? '' : 'SLP_TOKEN_TYPE_NFT1_CHILD');

  static const $core.List<SlpTokenType> values = <SlpTokenType>[
    SLP_TOKEN_TYPE_NONE,
    SLP_TOKEN_TYPE_FUNGIBLE,
    SLP_TOKEN_TYPE_MINT_VAULT,
    SLP_TOKEN_TYPE_NFT1_GROUP,
    SLP_TOKEN_TYPE_NFT1_CHILD,
  ];

  static final $core.Map<$core.int, SlpTokenType> _byValue =
      $pb.ProtobufEnum.initByValue(values);
  static SlpTokenType? valueOf($core.int value) => _byValue[value];

  const SlpTokenType._(super.value, super.name);
}

/// SLP/ALP tx type
class TokenTxType extends $pb.ProtobufEnum {
  /// No tx type, e.g. when input tokens are burned
  static const TokenTxType NONE =
      TokenTxType._(0, _omitEnumNames ? '' : 'NONE');

  /// Unknown tx type, i.e. for unknown token types
  static const TokenTxType UNKNOWN =
      TokenTxType._(1, _omitEnumNames ? '' : 'UNKNOWN');

  /// GENESIS tx
  static const TokenTxType GENESIS =
      TokenTxType._(2, _omitEnumNames ? '' : 'GENESIS');

  /// SEND tx
  static const TokenTxType SEND =
      TokenTxType._(3, _omitEnumNames ? '' : 'SEND');

  /// MINT tx
  static const TokenTxType MINT =
      TokenTxType._(4, _omitEnumNames ? '' : 'MINT');

  /// BURN tx
  static const TokenTxType BURN =
      TokenTxType._(5, _omitEnumNames ? '' : 'BURN');

  static const $core.List<TokenTxType> values = <TokenTxType>[
    NONE,
    UNKNOWN,
    GENESIS,
    SEND,
    MINT,
    BURN,
  ];

  static final $core.List<TokenTxType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 5);
  static TokenTxType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const TokenTxType._(super.value, super.name);
}

/// Type of message for the block
class BlockMsgType extends $pb.ProtobufEnum {
  /// Block connected to the blockchain
  static const BlockMsgType BLK_CONNECTED =
      BlockMsgType._(0, _omitEnumNames ? '' : 'BLK_CONNECTED');

  /// Block disconnected from the blockchain
  static const BlockMsgType BLK_DISCONNECTED =
      BlockMsgType._(1, _omitEnumNames ? '' : 'BLK_DISCONNECTED');

  /// Block has been finalized by Avalanche
  static const BlockMsgType BLK_FINALIZED =
      BlockMsgType._(2, _omitEnumNames ? '' : 'BLK_FINALIZED');

  /// Block has been invalidated by Avalanche
  static const BlockMsgType BLK_INVALIDATED =
      BlockMsgType._(3, _omitEnumNames ? '' : 'BLK_INVALIDATED');

  static const $core.List<BlockMsgType> values = <BlockMsgType>[
    BLK_CONNECTED,
    BLK_DISCONNECTED,
    BLK_FINALIZED,
    BLK_INVALIDATED,
  ];

  static final $core.List<BlockMsgType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 3);
  static BlockMsgType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const BlockMsgType._(super.value, super.name);
}

/// Type of tx finalization
class TxFinalizationReasonType extends $pb.ProtobufEnum {
  /// The transaction is finalized by post-consensus
  static const TxFinalizationReasonType TX_FINALIZATION_REASON_POST_CONSENSUS =
      TxFinalizationReasonType._(
          0, _omitEnumNames ? '' : 'TX_FINALIZATION_REASON_POST_CONSENSUS');

  /// The transaction is finalized by pre-consensus
  static const TxFinalizationReasonType TX_FINALIZATION_REASON_PRE_CONSENSUS =
      TxFinalizationReasonType._(
          1, _omitEnumNames ? '' : 'TX_FINALIZATION_REASON_PRE_CONSENSUS');

  static const $core.List<TxFinalizationReasonType> values =
      <TxFinalizationReasonType>[
    TX_FINALIZATION_REASON_POST_CONSENSUS,
    TX_FINALIZATION_REASON_PRE_CONSENSUS,
  ];

  static final $core.List<TxFinalizationReasonType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 1);
  static TxFinalizationReasonType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const TxFinalizationReasonType._(super.value, super.name);
}

/// Type of message for a tx
class TxMsgType extends $pb.ProtobufEnum {
  /// Tx added to the mempool
  static const TxMsgType TX_ADDED_TO_MEMPOOL =
      TxMsgType._(0, _omitEnumNames ? '' : 'TX_ADDED_TO_MEMPOOL');

  /// Tx removed from the mempool
  static const TxMsgType TX_REMOVED_FROM_MEMPOOL =
      TxMsgType._(1, _omitEnumNames ? '' : 'TX_REMOVED_FROM_MEMPOOL');

  /// Tx confirmed in a block
  static const TxMsgType TX_CONFIRMED =
      TxMsgType._(2, _omitEnumNames ? '' : 'TX_CONFIRMED');

  /// Tx finalized by Avalanche
  static const TxMsgType TX_FINALIZED =
      TxMsgType._(3, _omitEnumNames ? '' : 'TX_FINALIZED');

  /// Tx invalidated by Avalanche
  static const TxMsgType TX_INVALIDATED =
      TxMsgType._(4, _omitEnumNames ? '' : 'TX_INVALIDATED');

  static const $core.List<TxMsgType> values = <TxMsgType>[
    TX_ADDED_TO_MEMPOOL,
    TX_REMOVED_FROM_MEMPOOL,
    TX_CONFIRMED,
    TX_FINALIZED,
    TX_INVALIDATED,
  ];

  static final $core.List<TxMsgType?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 4);
  static TxMsgType? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const TxMsgType._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
