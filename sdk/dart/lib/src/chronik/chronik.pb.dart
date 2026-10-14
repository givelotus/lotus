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

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'chronik.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'chronik.pbenum.dart';

/// Block on the blockchain
class Block extends $pb.GeneratedMessage {
  factory Block({
    BlockInfo? blockInfo,
  }) {
    final result = Block._();
    if (blockInfo != null) result.blockInfo = blockInfo;
    return result;
  }

  Block._();

  factory Block.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Block()..mergeFromBuffer(data, registry);
  factory Block.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Block()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Block',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Block.$_createMessage)
    ..aOM<BlockInfo>(1, _omitFieldNames ? '' : 'blockInfo',
        subBuilder: BlockInfo.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Block clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Block copyWith(void Function(Block) updates) =>
      super.copyWith((message) => updates(message as Block)) as Block;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Block() / Block.new instead')
  static Block create() => Block._();
  static $pb.GeneratedMessage $_createMessage() => Block._();
  @$core.override
  Block createEmptyInstance() => Block._();
  @$core.pragma('dart2js:noInline')
  static Block getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Block>(Block.$_createMessage);
  static Block? _defaultInstance;

  /// Info about the block
  @$pb.TagNumber(1)
  BlockInfo get blockInfo => $_getN(0);
  @$pb.TagNumber(1)
  set blockInfo(BlockInfo value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasBlockInfo() => $_has(0);
  @$pb.TagNumber(1)
  void clearBlockInfo() => $_clearField(1);
  @$pb.TagNumber(1)
  BlockInfo ensureBlockInfo() => $_ensure(0);
}

/// Range of blocks
class Blocks extends $pb.GeneratedMessage {
  factory Blocks({
    $core.Iterable<BlockInfo>? blocks,
  }) {
    final result = Blocks._();
    if (blocks != null) result.blocks.addAll(blocks);
    return result;
  }

  Blocks._();

  factory Blocks.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Blocks()..mergeFromBuffer(data, registry);
  factory Blocks.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Blocks()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Blocks',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Blocks.$_createMessage)
    ..pPM<BlockInfo>(1, _omitFieldNames ? '' : 'blocks',
        subBuilder: BlockInfo.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Blocks clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Blocks copyWith(void Function(Blocks) updates) =>
      super.copyWith((message) => updates(message as Blocks)) as Blocks;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Blocks() / Blocks.new instead')
  static Blocks create() => Blocks._();
  static $pb.GeneratedMessage $_createMessage() => Blocks._();
  @$core.override
  Blocks createEmptyInstance() => Blocks._();
  @$core.pragma('dart2js:noInline')
  static Blocks getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Blocks>(Blocks.$_createMessage);
  static Blocks? _defaultInstance;

  /// Queried blocks
  @$pb.TagNumber(1)
  $pb.PbList<BlockInfo> get blocks => $_getList(0);
}

/// Header on the blockchain
class BlockHeader extends $pb.GeneratedMessage {
  factory BlockHeader({
    $core.List<$core.int>? rawHeader,
    $core.List<$core.int>? root,
    $core.Iterable<$core.List<$core.int>>? branch,
  }) {
    final result = BlockHeader._();
    if (rawHeader != null) result.rawHeader = rawHeader;
    if (root != null) result.root = root;
    if (branch != null) result.branch.addAll(branch);
    return result;
  }

  BlockHeader._();

  factory BlockHeader.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockHeader()..mergeFromBuffer(data, registry);
  factory BlockHeader.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockHeader()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockHeader',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BlockHeader.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'rawHeader', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'root', $pb.PbFieldType.OY)
    ..p<$core.List<$core.int>>(
        3, _omitFieldNames ? '' : 'branch', $pb.PbFieldType.PY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockHeader clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockHeader copyWith(void Function(BlockHeader) updates) =>
      super.copyWith((message) => updates(message as BlockHeader))
          as BlockHeader;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BlockHeader() / BlockHeader.new instead')
  static BlockHeader create() => BlockHeader._();
  static $pb.GeneratedMessage $_createMessage() => BlockHeader._();
  @$core.override
  BlockHeader createEmptyInstance() => BlockHeader._();
  @$core.pragma('dart2js:noInline')
  static BlockHeader getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<BlockHeader>(
          BlockHeader.$_createMessage);
  static BlockHeader? _defaultInstance;

  /// Raw data
  @$pb.TagNumber(1)
  $core.List<$core.int> get rawHeader => $_getN(0);
  @$pb.TagNumber(1)
  set rawHeader($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRawHeader() => $_has(0);
  @$pb.TagNumber(1)
  void clearRawHeader() => $_clearField(1);

  /// Merkle root
  @$pb.TagNumber(2)
  $core.List<$core.int> get root => $_getN(1);
  @$pb.TagNumber(2)
  set root($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasRoot() => $_has(1);
  @$pb.TagNumber(2)
  void clearRoot() => $_clearField(2);

  /// Merkle branch of header up to root, deepest pairing first
  @$pb.TagNumber(3)
  $pb.PbList<$core.List<$core.int>> get branch => $_getList(2);
}

/// Range of headers
class BlockHeaders extends $pb.GeneratedMessage {
  factory BlockHeaders({
    $core.Iterable<BlockHeader>? headers,
  }) {
    final result = BlockHeaders._();
    if (headers != null) result.headers.addAll(headers);
    return result;
  }

  BlockHeaders._();

  factory BlockHeaders.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockHeaders()..mergeFromBuffer(data, registry);
  factory BlockHeaders.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockHeaders()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockHeaders',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BlockHeaders.$_createMessage)
    ..pPM<BlockHeader>(1, _omitFieldNames ? '' : 'headers',
        subBuilder: BlockHeader.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockHeaders clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockHeaders copyWith(void Function(BlockHeaders) updates) =>
      super.copyWith((message) => updates(message as BlockHeaders))
          as BlockHeaders;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BlockHeaders() / BlockHeaders.new instead')
  static BlockHeaders create() => BlockHeaders._();
  static $pb.GeneratedMessage $_createMessage() => BlockHeaders._();
  @$core.override
  BlockHeaders createEmptyInstance() => BlockHeaders._();
  @$core.pragma('dart2js:noInline')
  static BlockHeaders getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<BlockHeaders>(
          BlockHeaders.$_createMessage);
  static BlockHeaders? _defaultInstance;

  /// Queried headers
  @$pb.TagNumber(1)
  $pb.PbList<BlockHeader> get headers => $_getList(0);
}

/// Info about the state of the blockchain.
class BlockchainInfo extends $pb.GeneratedMessage {
  factory BlockchainInfo({
    $core.List<$core.int>? tipHash,
    $core.int? tipHeight,
  }) {
    final result = BlockchainInfo._();
    if (tipHash != null) result.tipHash = tipHash;
    if (tipHeight != null) result.tipHeight = tipHeight;
    return result;
  }

  BlockchainInfo._();

  factory BlockchainInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockchainInfo()..mergeFromBuffer(data, registry);
  factory BlockchainInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockchainInfo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockchainInfo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BlockchainInfo.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'tipHash', $pb.PbFieldType.OY)
    ..aI(2, _omitFieldNames ? '' : 'tipHeight')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockchainInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockchainInfo copyWith(void Function(BlockchainInfo) updates) =>
      super.copyWith((message) => updates(message as BlockchainInfo))
          as BlockchainInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BlockchainInfo() / BlockchainInfo.new instead')
  static BlockchainInfo create() => BlockchainInfo._();
  static $pb.GeneratedMessage $_createMessage() => BlockchainInfo._();
  @$core.override
  BlockchainInfo createEmptyInstance() => BlockchainInfo._();
  @$core.pragma('dart2js:noInline')
  static BlockchainInfo getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<BlockchainInfo>(
          BlockchainInfo.$_createMessage);
  static BlockchainInfo? _defaultInstance;

  /// Hash (little-endian) of the current tip
  @$pb.TagNumber(1)
  $core.List<$core.int> get tipHash => $_getN(0);
  @$pb.TagNumber(1)
  set tipHash($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTipHash() => $_has(0);
  @$pb.TagNumber(1)
  void clearTipHash() => $_clearField(1);

  /// Height of the current tip (genesis has height = 0)
  @$pb.TagNumber(2)
  $core.int get tipHeight => $_getIZ(1);
  @$pb.TagNumber(2)
  set tipHeight($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTipHeight() => $_has(1);
  @$pb.TagNumber(2)
  void clearTipHeight() => $_clearField(2);
}

/// Info about the chronik software this server is running
class ChronikInfo extends $pb.GeneratedMessage {
  factory ChronikInfo({
    $core.String? version,
  }) {
    final result = ChronikInfo._();
    if (version != null) result.version = version;
    return result;
  }

  ChronikInfo._();

  factory ChronikInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ChronikInfo()..mergeFromBuffer(data, registry);
  factory ChronikInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ChronikInfo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChronikInfo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ChronikInfo.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChronikInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChronikInfo copyWith(void Function(ChronikInfo) updates) =>
      super.copyWith((message) => updates(message as ChronikInfo))
          as ChronikInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use ChronikInfo() / ChronikInfo.new instead')
  static ChronikInfo create() => ChronikInfo._();
  static $pb.GeneratedMessage $_createMessage() => ChronikInfo._();
  @$core.override
  ChronikInfo createEmptyInstance() => ChronikInfo._();
  @$core.pragma('dart2js:noInline')
  static ChronikInfo getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChronikInfo>(
          ChronikInfo.$_createMessage);
  static ChronikInfo? _defaultInstance;

  /// chronik server version from chronik-http/Cargo.toml
  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => $_clearField(1);
}

/// Info about a block
class BlockInfo extends $pb.GeneratedMessage {
  factory BlockInfo({
    $core.List<$core.int>? hash,
    $core.List<$core.int>? prevHash,
    $core.int? height,
    $core.int? nBits,
    $fixnum.Int64? timestamp,
    $fixnum.Int64? blockSize,
    $fixnum.Int64? numTxs,
    $fixnum.Int64? numInputs,
    $fixnum.Int64? numOutputs,
    $fixnum.Int64? sumInputSats,
    $fixnum.Int64? sumCoinbaseOutputSats,
    $fixnum.Int64? sumNormalOutputSats,
    $fixnum.Int64? sumBurnedSats,
    $core.bool? isFinal,
  }) {
    final result = BlockInfo._();
    if (hash != null) result.hash = hash;
    if (prevHash != null) result.prevHash = prevHash;
    if (height != null) result.height = height;
    if (nBits != null) result.nBits = nBits;
    if (timestamp != null) result.timestamp = timestamp;
    if (blockSize != null) result.blockSize = blockSize;
    if (numTxs != null) result.numTxs = numTxs;
    if (numInputs != null) result.numInputs = numInputs;
    if (numOutputs != null) result.numOutputs = numOutputs;
    if (sumInputSats != null) result.sumInputSats = sumInputSats;
    if (sumCoinbaseOutputSats != null)
      result.sumCoinbaseOutputSats = sumCoinbaseOutputSats;
    if (sumNormalOutputSats != null)
      result.sumNormalOutputSats = sumNormalOutputSats;
    if (sumBurnedSats != null) result.sumBurnedSats = sumBurnedSats;
    if (isFinal != null) result.isFinal = isFinal;
    return result;
  }

  BlockInfo._();

  factory BlockInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockInfo()..mergeFromBuffer(data, registry);
  factory BlockInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockInfo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockInfo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BlockInfo.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'hash', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'prevHash', $pb.PbFieldType.OY)
    ..aI(3, _omitFieldNames ? '' : 'height')
    ..aI(4, _omitFieldNames ? '' : 'nBits', fieldType: $pb.PbFieldType.OU3)
    ..aInt64(5, _omitFieldNames ? '' : 'timestamp')
    ..a<$fixnum.Int64>(
        6, _omitFieldNames ? '' : 'blockSize', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..a<$fixnum.Int64>(7, _omitFieldNames ? '' : 'numTxs', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..a<$fixnum.Int64>(
        8, _omitFieldNames ? '' : 'numInputs', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..a<$fixnum.Int64>(
        9, _omitFieldNames ? '' : 'numOutputs', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..aInt64(10, _omitFieldNames ? '' : 'sumInputSats')
    ..aInt64(11, _omitFieldNames ? '' : 'sumCoinbaseOutputSats')
    ..aInt64(12, _omitFieldNames ? '' : 'sumNormalOutputSats')
    ..aInt64(13, _omitFieldNames ? '' : 'sumBurnedSats')
    ..aOB(14, _omitFieldNames ? '' : 'isFinal')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockInfo copyWith(void Function(BlockInfo) updates) =>
      super.copyWith((message) => updates(message as BlockInfo)) as BlockInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BlockInfo() / BlockInfo.new instead')
  static BlockInfo create() => BlockInfo._();
  static $pb.GeneratedMessage $_createMessage() => BlockInfo._();
  @$core.override
  BlockInfo createEmptyInstance() => BlockInfo._();
  @$core.pragma('dart2js:noInline')
  static BlockInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BlockInfo>(BlockInfo.$_createMessage);
  static BlockInfo? _defaultInstance;

  /// Hash (little-endian)
  @$pb.TagNumber(1)
  $core.List<$core.int> get hash => $_getN(0);
  @$pb.TagNumber(1)
  set hash($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasHash() => $_has(0);
  @$pb.TagNumber(1)
  void clearHash() => $_clearField(1);

  /// Hash of the previous block (little-endian)
  @$pb.TagNumber(2)
  $core.List<$core.int> get prevHash => $_getN(1);
  @$pb.TagNumber(2)
  set prevHash($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPrevHash() => $_has(1);
  @$pb.TagNumber(2)
  void clearPrevHash() => $_clearField(2);

  /// Height in the chain
  @$pb.TagNumber(3)
  $core.int get height => $_getIZ(2);
  @$pb.TagNumber(3)
  set height($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasHeight() => $_has(2);
  @$pb.TagNumber(3)
  void clearHeight() => $_clearField(3);

  /// nBits field encoding the target
  @$pb.TagNumber(4)
  $core.int get nBits => $_getIZ(3);
  @$pb.TagNumber(4)
  set nBits($core.int value) => $_setUnsignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasNBits() => $_has(3);
  @$pb.TagNumber(4)
  void clearNBits() => $_clearField(4);

  /// Timestamp field of the block
  @$pb.TagNumber(5)
  $fixnum.Int64 get timestamp => $_getI64(4);
  @$pb.TagNumber(5)
  set timestamp($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasTimestamp() => $_has(4);
  @$pb.TagNumber(5)
  void clearTimestamp() => $_clearField(5);

  /// Block size of this block in bytes (including headers etc.)
  @$pb.TagNumber(6)
  $fixnum.Int64 get blockSize => $_getI64(5);
  @$pb.TagNumber(6)
  set blockSize($fixnum.Int64 value) => $_setInt64(5, value);
  @$pb.TagNumber(6)
  $core.bool hasBlockSize() => $_has(5);
  @$pb.TagNumber(6)
  void clearBlockSize() => $_clearField(6);

  /// Number of txs in this block
  @$pb.TagNumber(7)
  $fixnum.Int64 get numTxs => $_getI64(6);
  @$pb.TagNumber(7)
  set numTxs($fixnum.Int64 value) => $_setInt64(6, value);
  @$pb.TagNumber(7)
  $core.bool hasNumTxs() => $_has(6);
  @$pb.TagNumber(7)
  void clearNumTxs() => $_clearField(7);

  /// Total number of tx inputs in block (including coinbase)
  @$pb.TagNumber(8)
  $fixnum.Int64 get numInputs => $_getI64(7);
  @$pb.TagNumber(8)
  set numInputs($fixnum.Int64 value) => $_setInt64(7, value);
  @$pb.TagNumber(8)
  $core.bool hasNumInputs() => $_has(7);
  @$pb.TagNumber(8)
  void clearNumInputs() => $_clearField(8);

  /// Total number of tx output in block (including coinbase)
  @$pb.TagNumber(9)
  $fixnum.Int64 get numOutputs => $_getI64(8);
  @$pb.TagNumber(9)
  set numOutputs($fixnum.Int64 value) => $_setInt64(8, value);
  @$pb.TagNumber(9)
  $core.bool hasNumOutputs() => $_has(8);
  @$pb.TagNumber(9)
  void clearNumOutputs() => $_clearField(9);

  /// Total number of satoshis spent by tx inputs
  @$pb.TagNumber(10)
  $fixnum.Int64 get sumInputSats => $_getI64(9);
  @$pb.TagNumber(10)
  set sumInputSats($fixnum.Int64 value) => $_setInt64(9, value);
  @$pb.TagNumber(10)
  $core.bool hasSumInputSats() => $_has(9);
  @$pb.TagNumber(10)
  void clearSumInputSats() => $_clearField(10);

  /// Block reward for this block
  @$pb.TagNumber(11)
  $fixnum.Int64 get sumCoinbaseOutputSats => $_getI64(10);
  @$pb.TagNumber(11)
  set sumCoinbaseOutputSats($fixnum.Int64 value) => $_setInt64(10, value);
  @$pb.TagNumber(11)
  $core.bool hasSumCoinbaseOutputSats() => $_has(10);
  @$pb.TagNumber(11)
  void clearSumCoinbaseOutputSats() => $_clearField(11);

  /// Total number of satoshis in non-coinbase tx outputs
  @$pb.TagNumber(12)
  $fixnum.Int64 get sumNormalOutputSats => $_getI64(11);
  @$pb.TagNumber(12)
  set sumNormalOutputSats($fixnum.Int64 value) => $_setInt64(11, value);
  @$pb.TagNumber(12)
  $core.bool hasSumNormalOutputSats() => $_has(11);
  @$pb.TagNumber(12)
  void clearSumNormalOutputSats() => $_clearField(12);

  /// Total number of satoshis burned using OP_RETURN
  @$pb.TagNumber(13)
  $fixnum.Int64 get sumBurnedSats => $_getI64(12);
  @$pb.TagNumber(13)
  set sumBurnedSats($fixnum.Int64 value) => $_setInt64(12, value);
  @$pb.TagNumber(13)
  $core.bool hasSumBurnedSats() => $_has(12);
  @$pb.TagNumber(13)
  void clearSumBurnedSats() => $_clearField(13);

  /// Whether the block has been finalized by Avalanche
  @$pb.TagNumber(14)
  $core.bool get isFinal => $_getBF(13);
  @$pb.TagNumber(14)
  set isFinal($core.bool value) => $_setBool(13, value);
  @$pb.TagNumber(14)
  $core.bool hasIsFinal() => $_has(13);
  @$pb.TagNumber(14)
  void clearIsFinal() => $_clearField(14);
}

/// Details about a transaction
class Tx extends $pb.GeneratedMessage {
  factory Tx({
    $core.List<$core.int>? txid,
    $core.int? version,
    $core.Iterable<TxInput>? inputs,
    $core.Iterable<TxOutput>? outputs,
    $core.int? lockTime,
    BlockMetadata? block,
    $fixnum.Int64? timeFirstSeen,
    $core.int? size,
    $core.bool? isCoinbase,
    $core.Iterable<TokenEntry>? tokenEntries,
    $core.Iterable<TokenFailedParsing>? tokenFailedParsings,
    TokenStatus? tokenStatus,
    $core.bool? isFinal,
  }) {
    final result = Tx._();
    if (txid != null) result.txid = txid;
    if (version != null) result.version = version;
    if (inputs != null) result.inputs.addAll(inputs);
    if (outputs != null) result.outputs.addAll(outputs);
    if (lockTime != null) result.lockTime = lockTime;
    if (block != null) result.block = block;
    if (timeFirstSeen != null) result.timeFirstSeen = timeFirstSeen;
    if (size != null) result.size = size;
    if (isCoinbase != null) result.isCoinbase = isCoinbase;
    if (tokenEntries != null) result.tokenEntries.addAll(tokenEntries);
    if (tokenFailedParsings != null)
      result.tokenFailedParsings.addAll(tokenFailedParsings);
    if (tokenStatus != null) result.tokenStatus = tokenStatus;
    if (isFinal != null) result.isFinal = isFinal;
    return result;
  }

  Tx._();

  factory Tx.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Tx()..mergeFromBuffer(data, registry);
  factory Tx.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Tx()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Tx',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Tx.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'txid', $pb.PbFieldType.OY)
    ..aI(2, _omitFieldNames ? '' : 'version', fieldType: $pb.PbFieldType.OU3)
    ..pPM<TxInput>(3, _omitFieldNames ? '' : 'inputs',
        subBuilder: TxInput.$_createMessage)
    ..pPM<TxOutput>(4, _omitFieldNames ? '' : 'outputs',
        subBuilder: TxOutput.$_createMessage)
    ..aI(5, _omitFieldNames ? '' : 'lockTime', fieldType: $pb.PbFieldType.OU3)
    ..aOM<BlockMetadata>(8, _omitFieldNames ? '' : 'block',
        subBuilder: BlockMetadata.$_createMessage)
    ..aInt64(9, _omitFieldNames ? '' : 'timeFirstSeen')
    ..aI(11, _omitFieldNames ? '' : 'size', fieldType: $pb.PbFieldType.OU3)
    ..aOB(12, _omitFieldNames ? '' : 'isCoinbase')
    ..pPM<TokenEntry>(13, _omitFieldNames ? '' : 'tokenEntries',
        subBuilder: TokenEntry.$_createMessage)
    ..pPM<TokenFailedParsing>(14, _omitFieldNames ? '' : 'tokenFailedParsings',
        subBuilder: TokenFailedParsing.$_createMessage)
    ..aE<TokenStatus>(15, _omitFieldNames ? '' : 'tokenStatus',
        enumValues: TokenStatus.values)
    ..aOB(16, _omitFieldNames ? '' : 'isFinal')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Tx clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Tx copyWith(void Function(Tx) updates) =>
      super.copyWith((message) => updates(message as Tx)) as Tx;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Tx() / Tx.new instead')
  static Tx create() => Tx._();
  static $pb.GeneratedMessage $_createMessage() => Tx._();
  @$core.override
  Tx createEmptyInstance() => Tx._();
  @$core.pragma('dart2js:noInline')
  static Tx getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Tx>(Tx.$_createMessage);
  static Tx? _defaultInstance;

  /// TxId (little-endian) of the tx
  @$pb.TagNumber(1)
  $core.List<$core.int> get txid => $_getN(0);
  @$pb.TagNumber(1)
  set txid($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTxid() => $_has(0);
  @$pb.TagNumber(1)
  void clearTxid() => $_clearField(1);

  /// nVersion
  @$pb.TagNumber(2)
  $core.int get version => $_getIZ(1);
  @$pb.TagNumber(2)
  set version($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasVersion() => $_has(1);
  @$pb.TagNumber(2)
  void clearVersion() => $_clearField(2);

  /// Inputs of the tx (aka. `vin`)
  @$pb.TagNumber(3)
  $pb.PbList<TxInput> get inputs => $_getList(2);

  /// Outputs of the tx (aka. `vout`)
  @$pb.TagNumber(4)
  $pb.PbList<TxOutput> get outputs => $_getList(3);

  /// nLockTime
  @$pb.TagNumber(5)
  $core.int get lockTime => $_getIZ(4);
  @$pb.TagNumber(5)
  set lockTime($core.int value) => $_setUnsignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasLockTime() => $_has(4);
  @$pb.TagNumber(5)
  void clearLockTime() => $_clearField(5);

  /// Which block this tx is in, or None, if in the mempool
  @$pb.TagNumber(8)
  BlockMetadata get block => $_getN(5);
  @$pb.TagNumber(8)
  set block(BlockMetadata value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasBlock() => $_has(5);
  @$pb.TagNumber(8)
  void clearBlock() => $_clearField(8);
  @$pb.TagNumber(8)
  BlockMetadata ensureBlock() => $_ensure(5);

  /// Time this tx has first been added to the mempool, or 0 if unknown
  @$pb.TagNumber(9)
  $fixnum.Int64 get timeFirstSeen => $_getI64(6);
  @$pb.TagNumber(9)
  set timeFirstSeen($fixnum.Int64 value) => $_setInt64(6, value);
  @$pb.TagNumber(9)
  $core.bool hasTimeFirstSeen() => $_has(6);
  @$pb.TagNumber(9)
  void clearTimeFirstSeen() => $_clearField(9);

  /// Serialized size of the tx
  @$pb.TagNumber(11)
  $core.int get size => $_getIZ(7);
  @$pb.TagNumber(11)
  set size($core.int value) => $_setUnsignedInt32(7, value);
  @$pb.TagNumber(11)
  $core.bool hasSize() => $_has(7);
  @$pb.TagNumber(11)
  void clearSize() => $_clearField(11);

  /// Whether this tx is a coinbase tx
  @$pb.TagNumber(12)
  $core.bool get isCoinbase => $_getBF(8);
  @$pb.TagNumber(12)
  set isCoinbase($core.bool value) => $_setBool(8, value);
  @$pb.TagNumber(12)
  $core.bool hasIsCoinbase() => $_has(8);
  @$pb.TagNumber(12)
  void clearIsCoinbase() => $_clearField(12);

  /// Tokens involved in this txs
  @$pb.TagNumber(13)
  $pb.PbList<TokenEntry> get tokenEntries => $_getList(9);

  /// Failed parsing attempts of this tx
  @$pb.TagNumber(14)
  $pb.PbList<TokenFailedParsing> get tokenFailedParsings => $_getList(10);

  /// Token status, i.e. whether this tx has any tokens or unintentional token burns
  /// or something unexpected, like failed parsings etc.
  @$pb.TagNumber(15)
  TokenStatus get tokenStatus => $_getN(11);
  @$pb.TagNumber(15)
  set tokenStatus(TokenStatus value) => $_setField(15, value);
  @$pb.TagNumber(15)
  $core.bool hasTokenStatus() => $_has(11);
  @$pb.TagNumber(15)
  void clearTokenStatus() => $_clearField(15);

  /// Whether the transaction has been finalized by avalanche
  @$pb.TagNumber(16)
  $core.bool get isFinal => $_getBF(12);
  @$pb.TagNumber(16)
  set isFinal($core.bool value) => $_setBool(12, value);
  @$pb.TagNumber(16)
  $core.bool hasIsFinal() => $_has(12);
  @$pb.TagNumber(16)
  void clearIsFinal() => $_clearField(16);
}

/// UTXO of a script.
class ScriptUtxo extends $pb.GeneratedMessage {
  factory ScriptUtxo({
    OutPoint? outpoint,
    $core.int? blockHeight,
    $core.bool? isCoinbase,
    $fixnum.Int64? sats,
    $core.bool? isFinal,
    Token? token,
    $core.Iterable<$core.MapEntry<$core.String, PluginEntry>>? plugins,
  }) {
    final result = ScriptUtxo._();
    if (outpoint != null) result.outpoint = outpoint;
    if (blockHeight != null) result.blockHeight = blockHeight;
    if (isCoinbase != null) result.isCoinbase = isCoinbase;
    if (sats != null) result.sats = sats;
    if (isFinal != null) result.isFinal = isFinal;
    if (token != null) result.token = token;
    if (plugins != null) result.plugins.addEntries(plugins);
    return result;
  }

  ScriptUtxo._();

  factory ScriptUtxo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptUtxo()..mergeFromBuffer(data, registry);
  factory ScriptUtxo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptUtxo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptUtxo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptUtxo.$_createMessage)
    ..aOM<OutPoint>(1, _omitFieldNames ? '' : 'outpoint',
        subBuilder: OutPoint.$_createMessage)
    ..aI(2, _omitFieldNames ? '' : 'blockHeight')
    ..aOB(3, _omitFieldNames ? '' : 'isCoinbase')
    ..aInt64(5, _omitFieldNames ? '' : 'sats')
    ..aOB(10, _omitFieldNames ? '' : 'isFinal')
    ..aOM<Token>(11, _omitFieldNames ? '' : 'token',
        subBuilder: Token.$_createMessage)
    ..m<$core.String, PluginEntry>(12, _omitFieldNames ? '' : 'plugins',
        entryClassName: 'ScriptUtxo.PluginsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OM,
        valueCreator: PluginEntry.$_createMessage,
        valueDefaultOrMaker: PluginEntry.getDefault,
        packageName: const $pb.PackageName('chronik'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptUtxo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptUtxo copyWith(void Function(ScriptUtxo) updates) =>
      super.copyWith((message) => updates(message as ScriptUtxo)) as ScriptUtxo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use ScriptUtxo() / ScriptUtxo.new instead')
  static ScriptUtxo create() => ScriptUtxo._();
  static $pb.GeneratedMessage $_createMessage() => ScriptUtxo._();
  @$core.override
  ScriptUtxo createEmptyInstance() => ScriptUtxo._();
  @$core.pragma('dart2js:noInline')
  static ScriptUtxo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptUtxo>(ScriptUtxo.$_createMessage);
  static ScriptUtxo? _defaultInstance;

  /// txid and out_idx of the unspent output.
  @$pb.TagNumber(1)
  OutPoint get outpoint => $_getN(0);
  @$pb.TagNumber(1)
  set outpoint(OutPoint value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasOutpoint() => $_has(0);
  @$pb.TagNumber(1)
  void clearOutpoint() => $_clearField(1);
  @$pb.TagNumber(1)
  OutPoint ensureOutpoint() => $_ensure(0);

  /// Block height of the UTXO, or -1 if in mempool.
  @$pb.TagNumber(2)
  $core.int get blockHeight => $_getIZ(1);
  @$pb.TagNumber(2)
  set blockHeight($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasBlockHeight() => $_has(1);
  @$pb.TagNumber(2)
  void clearBlockHeight() => $_clearField(2);

  /// Whether the UTXO has been created in a coinbase tx.
  @$pb.TagNumber(3)
  $core.bool get isCoinbase => $_getBF(2);
  @$pb.TagNumber(3)
  set isCoinbase($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasIsCoinbase() => $_has(2);
  @$pb.TagNumber(3)
  void clearIsCoinbase() => $_clearField(3);

  /// Value of the output, in satoshis.
  @$pb.TagNumber(5)
  $fixnum.Int64 get sats => $_getI64(3);
  @$pb.TagNumber(5)
  set sats($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(5)
  $core.bool hasSats() => $_has(3);
  @$pb.TagNumber(5)
  void clearSats() => $_clearField(5);

  /// Whether the UTXO has been finalized by Avalanche.
  @$pb.TagNumber(10)
  $core.bool get isFinal => $_getBF(4);
  @$pb.TagNumber(10)
  set isFinal($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(10)
  $core.bool hasIsFinal() => $_has(4);
  @$pb.TagNumber(10)
  void clearIsFinal() => $_clearField(10);

  /// Token value attached to this UTXO
  @$pb.TagNumber(11)
  Token get token => $_getN(5);
  @$pb.TagNumber(11)
  set token(Token value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasToken() => $_has(5);
  @$pb.TagNumber(11)
  void clearToken() => $_clearField(11);
  @$pb.TagNumber(11)
  Token ensureToken() => $_ensure(5);

  /// Data attached to this output by plugins
  @$pb.TagNumber(12)
  $pb.PbMap<$core.String, PluginEntry> get plugins => $_getMap(6);
}

/// UTXO, but with a script attached.
class Utxo extends $pb.GeneratedMessage {
  factory Utxo({
    OutPoint? outpoint,
    $core.int? blockHeight,
    $core.bool? isCoinbase,
    $fixnum.Int64? sats,
    $core.List<$core.int>? script,
    $core.bool? isFinal,
    Token? token,
    $core.Iterable<$core.MapEntry<$core.String, PluginEntry>>? plugins,
  }) {
    final result = Utxo._();
    if (outpoint != null) result.outpoint = outpoint;
    if (blockHeight != null) result.blockHeight = blockHeight;
    if (isCoinbase != null) result.isCoinbase = isCoinbase;
    if (sats != null) result.sats = sats;
    if (script != null) result.script = script;
    if (isFinal != null) result.isFinal = isFinal;
    if (token != null) result.token = token;
    if (plugins != null) result.plugins.addEntries(plugins);
    return result;
  }

  Utxo._();

  factory Utxo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Utxo()..mergeFromBuffer(data, registry);
  factory Utxo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Utxo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Utxo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Utxo.$_createMessage)
    ..aOM<OutPoint>(1, _omitFieldNames ? '' : 'outpoint',
        subBuilder: OutPoint.$_createMessage)
    ..aI(2, _omitFieldNames ? '' : 'blockHeight')
    ..aOB(3, _omitFieldNames ? '' : 'isCoinbase')
    ..aInt64(4, _omitFieldNames ? '' : 'sats')
    ..a<$core.List<$core.int>>(
        5, _omitFieldNames ? '' : 'script', $pb.PbFieldType.OY)
    ..aOB(6, _omitFieldNames ? '' : 'isFinal')
    ..aOM<Token>(7, _omitFieldNames ? '' : 'token',
        subBuilder: Token.$_createMessage)
    ..m<$core.String, PluginEntry>(8, _omitFieldNames ? '' : 'plugins',
        entryClassName: 'Utxo.PluginsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OM,
        valueCreator: PluginEntry.$_createMessage,
        valueDefaultOrMaker: PluginEntry.getDefault,
        packageName: const $pb.PackageName('chronik'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Utxo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Utxo copyWith(void Function(Utxo) updates) =>
      super.copyWith((message) => updates(message as Utxo)) as Utxo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Utxo() / Utxo.new instead')
  static Utxo create() => Utxo._();
  static $pb.GeneratedMessage $_createMessage() => Utxo._();
  @$core.override
  Utxo createEmptyInstance() => Utxo._();
  @$core.pragma('dart2js:noInline')
  static Utxo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Utxo>(Utxo.$_createMessage);
  static Utxo? _defaultInstance;

  /// txid and out_idx of the unspent output.
  @$pb.TagNumber(1)
  OutPoint get outpoint => $_getN(0);
  @$pb.TagNumber(1)
  set outpoint(OutPoint value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasOutpoint() => $_has(0);
  @$pb.TagNumber(1)
  void clearOutpoint() => $_clearField(1);
  @$pb.TagNumber(1)
  OutPoint ensureOutpoint() => $_ensure(0);

  /// Block height of the UTXO, or -1 if in mempool.
  @$pb.TagNumber(2)
  $core.int get blockHeight => $_getIZ(1);
  @$pb.TagNumber(2)
  set blockHeight($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasBlockHeight() => $_has(1);
  @$pb.TagNumber(2)
  void clearBlockHeight() => $_clearField(2);

  /// Whether the UTXO has been created in a coinbase tx.
  @$pb.TagNumber(3)
  $core.bool get isCoinbase => $_getBF(2);
  @$pb.TagNumber(3)
  set isCoinbase($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasIsCoinbase() => $_has(2);
  @$pb.TagNumber(3)
  void clearIsCoinbase() => $_clearField(3);

  /// Value of the output, in satoshis.
  @$pb.TagNumber(4)
  $fixnum.Int64 get sats => $_getI64(3);
  @$pb.TagNumber(4)
  set sats($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSats() => $_has(3);
  @$pb.TagNumber(4)
  void clearSats() => $_clearField(4);

  /// Bytecode of the script of the output
  @$pb.TagNumber(5)
  $core.List<$core.int> get script => $_getN(4);
  @$pb.TagNumber(5)
  set script($core.List<$core.int> value) => $_setBytes(4, value);
  @$pb.TagNumber(5)
  $core.bool hasScript() => $_has(4);
  @$pb.TagNumber(5)
  void clearScript() => $_clearField(5);

  /// Whether the UTXO has been finalized by Avalanche.
  @$pb.TagNumber(6)
  $core.bool get isFinal => $_getBF(5);
  @$pb.TagNumber(6)
  set isFinal($core.bool value) => $_setBool(5, value);
  @$pb.TagNumber(6)
  $core.bool hasIsFinal() => $_has(5);
  @$pb.TagNumber(6)
  void clearIsFinal() => $_clearField(6);

  /// Token value attached to this UTXO
  @$pb.TagNumber(7)
  Token get token => $_getN(6);
  @$pb.TagNumber(7)
  set token(Token value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasToken() => $_has(6);
  @$pb.TagNumber(7)
  void clearToken() => $_clearField(7);
  @$pb.TagNumber(7)
  Token ensureToken() => $_ensure(6);

  /// Data attached to this output by plugins
  @$pb.TagNumber(8)
  $pb.PbMap<$core.String, PluginEntry> get plugins => $_getMap(7);
}

/// COutPoint, points to a coin being spent by an input.
class OutPoint extends $pb.GeneratedMessage {
  factory OutPoint({
    $core.List<$core.int>? txid,
    $core.int? outIdx,
  }) {
    final result = OutPoint._();
    if (txid != null) result.txid = txid;
    if (outIdx != null) result.outIdx = outIdx;
    return result;
  }

  OutPoint._();

  factory OutPoint.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      OutPoint()..mergeFromBuffer(data, registry);
  factory OutPoint.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      OutPoint()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'OutPoint',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: OutPoint.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'txid', $pb.PbFieldType.OY)
    ..aI(2, _omitFieldNames ? '' : 'outIdx', fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OutPoint clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  OutPoint copyWith(void Function(OutPoint) updates) =>
      super.copyWith((message) => updates(message as OutPoint)) as OutPoint;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use OutPoint() / OutPoint.new instead')
  static OutPoint create() => OutPoint._();
  static $pb.GeneratedMessage $_createMessage() => OutPoint._();
  @$core.override
  OutPoint createEmptyInstance() => OutPoint._();
  @$core.pragma('dart2js:noInline')
  static OutPoint getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<OutPoint>(OutPoint.$_createMessage);
  static OutPoint? _defaultInstance;

  /// TxId of the tx of the output being spent.
  @$pb.TagNumber(1)
  $core.List<$core.int> get txid => $_getN(0);
  @$pb.TagNumber(1)
  set txid($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTxid() => $_has(0);
  @$pb.TagNumber(1)
  void clearTxid() => $_clearField(1);

  /// Index of the output spent within the transaction.
  @$pb.TagNumber(2)
  $core.int get outIdx => $_getIZ(1);
  @$pb.TagNumber(2)
  set outIdx($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasOutIdx() => $_has(1);
  @$pb.TagNumber(2)
  void clearOutIdx() => $_clearField(2);
}

/// Points to an input spending a coin.
class SpentBy extends $pb.GeneratedMessage {
  factory SpentBy({
    $core.List<$core.int>? txid,
    $core.int? inputIdx,
  }) {
    final result = SpentBy._();
    if (txid != null) result.txid = txid;
    if (inputIdx != null) result.inputIdx = inputIdx;
    return result;
  }

  SpentBy._();

  factory SpentBy.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      SpentBy()..mergeFromBuffer(data, registry);
  factory SpentBy.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      SpentBy()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SpentBy',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: SpentBy.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'txid', $pb.PbFieldType.OY)
    ..aI(2, _omitFieldNames ? '' : 'inputIdx', fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SpentBy clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SpentBy copyWith(void Function(SpentBy) updates) =>
      super.copyWith((message) => updates(message as SpentBy)) as SpentBy;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use SpentBy() / SpentBy.new instead')
  static SpentBy create() => SpentBy._();
  static $pb.GeneratedMessage $_createMessage() => SpentBy._();
  @$core.override
  SpentBy createEmptyInstance() => SpentBy._();
  @$core.pragma('dart2js:noInline')
  static SpentBy getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SpentBy>(SpentBy.$_createMessage);
  static SpentBy? _defaultInstance;

  /// TxId of the tx with the input.
  @$pb.TagNumber(1)
  $core.List<$core.int> get txid => $_getN(0);
  @$pb.TagNumber(1)
  set txid($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTxid() => $_has(0);
  @$pb.TagNumber(1)
  void clearTxid() => $_clearField(1);

  /// Index in the inputs of the tx.
  @$pb.TagNumber(2)
  $core.int get inputIdx => $_getIZ(1);
  @$pb.TagNumber(2)
  set inputIdx($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasInputIdx() => $_has(1);
  @$pb.TagNumber(2)
  void clearInputIdx() => $_clearField(2);
}

/// CTxIn, spends a coin.
class TxInput extends $pb.GeneratedMessage {
  factory TxInput({
    OutPoint? prevOut,
    $core.List<$core.int>? inputScript,
    $core.List<$core.int>? outputScript,
    $fixnum.Int64? sats,
    $core.int? sequenceNo,
    Token? token,
    $core.Iterable<$core.MapEntry<$core.String, PluginEntry>>? plugins,
  }) {
    final result = TxInput._();
    if (prevOut != null) result.prevOut = prevOut;
    if (inputScript != null) result.inputScript = inputScript;
    if (outputScript != null) result.outputScript = outputScript;
    if (sats != null) result.sats = sats;
    if (sequenceNo != null) result.sequenceNo = sequenceNo;
    if (token != null) result.token = token;
    if (plugins != null) result.plugins.addEntries(plugins);
    return result;
  }

  TxInput._();

  factory TxInput.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxInput()..mergeFromBuffer(data, registry);
  factory TxInput.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxInput()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TxInput',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TxInput.$_createMessage)
    ..aOM<OutPoint>(1, _omitFieldNames ? '' : 'prevOut',
        subBuilder: OutPoint.$_createMessage)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'inputScript', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        3, _omitFieldNames ? '' : 'outputScript', $pb.PbFieldType.OY)
    ..aInt64(4, _omitFieldNames ? '' : 'sats')
    ..aI(5, _omitFieldNames ? '' : 'sequenceNo', fieldType: $pb.PbFieldType.OU3)
    ..aOM<Token>(8, _omitFieldNames ? '' : 'token',
        subBuilder: Token.$_createMessage)
    ..m<$core.String, PluginEntry>(9, _omitFieldNames ? '' : 'plugins',
        entryClassName: 'TxInput.PluginsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OM,
        valueCreator: PluginEntry.$_createMessage,
        valueDefaultOrMaker: PluginEntry.getDefault,
        packageName: const $pb.PackageName('chronik'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxInput clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxInput copyWith(void Function(TxInput) updates) =>
      super.copyWith((message) => updates(message as TxInput)) as TxInput;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TxInput() / TxInput.new instead')
  static TxInput create() => TxInput._();
  static $pb.GeneratedMessage $_createMessage() => TxInput._();
  @$core.override
  TxInput createEmptyInstance() => TxInput._();
  @$core.pragma('dart2js:noInline')
  static TxInput getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TxInput>(TxInput.$_createMessage);
  static TxInput? _defaultInstance;

  /// Reference to the coin being spent.
  @$pb.TagNumber(1)
  OutPoint get prevOut => $_getN(0);
  @$pb.TagNumber(1)
  set prevOut(OutPoint value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasPrevOut() => $_has(0);
  @$pb.TagNumber(1)
  void clearPrevOut() => $_clearField(1);
  @$pb.TagNumber(1)
  OutPoint ensurePrevOut() => $_ensure(0);

  /// scriptSig, script unlocking the coin.
  @$pb.TagNumber(2)
  $core.List<$core.int> get inputScript => $_getN(1);
  @$pb.TagNumber(2)
  set inputScript($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasInputScript() => $_has(1);
  @$pb.TagNumber(2)
  void clearInputScript() => $_clearField(2);

  /// scriptPubKey, script of the output locking the coin.
  @$pb.TagNumber(3)
  $core.List<$core.int> get outputScript => $_getN(2);
  @$pb.TagNumber(3)
  set outputScript($core.List<$core.int> value) => $_setBytes(2, value);
  @$pb.TagNumber(3)
  $core.bool hasOutputScript() => $_has(2);
  @$pb.TagNumber(3)
  void clearOutputScript() => $_clearField(3);

  /// value of the output being spent, in satoshis.
  @$pb.TagNumber(4)
  $fixnum.Int64 get sats => $_getI64(3);
  @$pb.TagNumber(4)
  set sats($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSats() => $_has(3);
  @$pb.TagNumber(4)
  void clearSats() => $_clearField(4);

  /// nSequence of the input.
  @$pb.TagNumber(5)
  $core.int get sequenceNo => $_getIZ(4);
  @$pb.TagNumber(5)
  set sequenceNo($core.int value) => $_setUnsignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasSequenceNo() => $_has(4);
  @$pb.TagNumber(5)
  void clearSequenceNo() => $_clearField(5);

  /// Token value attached to this input
  @$pb.TagNumber(8)
  Token get token => $_getN(5);
  @$pb.TagNumber(8)
  set token(Token value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasToken() => $_has(5);
  @$pb.TagNumber(8)
  void clearToken() => $_clearField(8);
  @$pb.TagNumber(8)
  Token ensureToken() => $_ensure(5);

  /// Data attached to this output by plugins
  @$pb.TagNumber(9)
  $pb.PbMap<$core.String, PluginEntry> get plugins => $_getMap(6);
}

/// CTxOut, creates a new coin.
class TxOutput extends $pb.GeneratedMessage {
  factory TxOutput({
    $fixnum.Int64? sats,
    $core.List<$core.int>? outputScript,
    SpentBy? spentBy,
    Token? token,
    $core.Iterable<$core.MapEntry<$core.String, PluginEntry>>? plugins,
  }) {
    final result = TxOutput._();
    if (sats != null) result.sats = sats;
    if (outputScript != null) result.outputScript = outputScript;
    if (spentBy != null) result.spentBy = spentBy;
    if (token != null) result.token = token;
    if (plugins != null) result.plugins.addEntries(plugins);
    return result;
  }

  TxOutput._();

  factory TxOutput.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxOutput()..mergeFromBuffer(data, registry);
  factory TxOutput.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxOutput()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TxOutput',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TxOutput.$_createMessage)
    ..aInt64(1, _omitFieldNames ? '' : 'sats')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'outputScript', $pb.PbFieldType.OY)
    ..aOM<SpentBy>(4, _omitFieldNames ? '' : 'spentBy',
        subBuilder: SpentBy.$_createMessage)
    ..aOM<Token>(5, _omitFieldNames ? '' : 'token',
        subBuilder: Token.$_createMessage)
    ..m<$core.String, PluginEntry>(6, _omitFieldNames ? '' : 'plugins',
        entryClassName: 'TxOutput.PluginsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OM,
        valueCreator: PluginEntry.$_createMessage,
        valueDefaultOrMaker: PluginEntry.getDefault,
        packageName: const $pb.PackageName('chronik'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxOutput clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxOutput copyWith(void Function(TxOutput) updates) =>
      super.copyWith((message) => updates(message as TxOutput)) as TxOutput;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TxOutput() / TxOutput.new instead')
  static TxOutput create() => TxOutput._();
  static $pb.GeneratedMessage $_createMessage() => TxOutput._();
  @$core.override
  TxOutput createEmptyInstance() => TxOutput._();
  @$core.pragma('dart2js:noInline')
  static TxOutput getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TxOutput>(TxOutput.$_createMessage);
  static TxOutput? _defaultInstance;

  /// Value of the coin, in satoshis.
  @$pb.TagNumber(1)
  $fixnum.Int64 get sats => $_getI64(0);
  @$pb.TagNumber(1)
  set sats($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSats() => $_has(0);
  @$pb.TagNumber(1)
  void clearSats() => $_clearField(1);

  /// scriptPubKey, script locking the output.
  @$pb.TagNumber(2)
  $core.List<$core.int> get outputScript => $_getN(1);
  @$pb.TagNumber(2)
  set outputScript($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasOutputScript() => $_has(1);
  @$pb.TagNumber(2)
  void clearOutputScript() => $_clearField(2);

  /// Which tx and input spent this output, if any.
  @$pb.TagNumber(4)
  SpentBy get spentBy => $_getN(2);
  @$pb.TagNumber(4)
  set spentBy(SpentBy value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasSpentBy() => $_has(2);
  @$pb.TagNumber(4)
  void clearSpentBy() => $_clearField(4);
  @$pb.TagNumber(4)
  SpentBy ensureSpentBy() => $_ensure(2);

  /// Token value attached to this output
  @$pb.TagNumber(5)
  Token get token => $_getN(3);
  @$pb.TagNumber(5)
  set token(Token value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasToken() => $_has(3);
  @$pb.TagNumber(5)
  void clearToken() => $_clearField(5);
  @$pb.TagNumber(5)
  Token ensureToken() => $_ensure(3);

  /// Data attached to this output by plugins
  @$pb.TagNumber(6)
  $pb.PbMap<$core.String, PluginEntry> get plugins => $_getMap(4);
}

/// Data about a block which a Tx is in.
class BlockMetadata extends $pb.GeneratedMessage {
  factory BlockMetadata({
    $core.int? height,
    $core.List<$core.int>? hash,
    $fixnum.Int64? timestamp,
    $core.bool? isFinal,
  }) {
    final result = BlockMetadata._();
    if (height != null) result.height = height;
    if (hash != null) result.hash = hash;
    if (timestamp != null) result.timestamp = timestamp;
    if (isFinal != null) result.isFinal = isFinal;
    return result;
  }

  BlockMetadata._();

  factory BlockMetadata.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockMetadata()..mergeFromBuffer(data, registry);
  factory BlockMetadata.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BlockMetadata()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BlockMetadata',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BlockMetadata.$_createMessage)
    ..aI(1, _omitFieldNames ? '' : 'height')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'hash', $pb.PbFieldType.OY)
    ..aInt64(3, _omitFieldNames ? '' : 'timestamp')
    ..aOB(4, _omitFieldNames ? '' : 'isFinal')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockMetadata clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BlockMetadata copyWith(void Function(BlockMetadata) updates) =>
      super.copyWith((message) => updates(message as BlockMetadata))
          as BlockMetadata;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BlockMetadata() / BlockMetadata.new instead')
  static BlockMetadata create() => BlockMetadata._();
  static $pb.GeneratedMessage $_createMessage() => BlockMetadata._();
  @$core.override
  BlockMetadata createEmptyInstance() => BlockMetadata._();
  @$core.pragma('dart2js:noInline')
  static BlockMetadata getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<BlockMetadata>(
          BlockMetadata.$_createMessage);
  static BlockMetadata? _defaultInstance;

  /// Height of the block the tx is in.
  @$pb.TagNumber(1)
  $core.int get height => $_getIZ(0);
  @$pb.TagNumber(1)
  set height($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasHeight() => $_has(0);
  @$pb.TagNumber(1)
  void clearHeight() => $_clearField(1);

  /// Hash of the block the tx is in.
  @$pb.TagNumber(2)
  $core.List<$core.int> get hash => $_getN(1);
  @$pb.TagNumber(2)
  set hash($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasHash() => $_has(1);
  @$pb.TagNumber(2)
  void clearHash() => $_clearField(2);

  /// nTime of the block the tx is in.
  @$pb.TagNumber(3)
  $fixnum.Int64 get timestamp => $_getI64(2);
  @$pb.TagNumber(3)
  set timestamp($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTimestamp() => $_has(2);
  @$pb.TagNumber(3)
  void clearTimestamp() => $_clearField(3);

  /// Whether the block has been finalized by Avalanche.
  @$pb.TagNumber(4)
  $core.bool get isFinal => $_getBF(3);
  @$pb.TagNumber(4)
  set isFinal($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasIsFinal() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsFinal() => $_clearField(4);
}

enum TokenType_TokenType { slp, alp, notSet }

/// SLP/ALP token type
class TokenType extends $pb.GeneratedMessage {
  factory TokenType({
    SlpTokenType? slp,
    AlpTokenType? alp,
  }) {
    final result = TokenType._();
    if (slp != null) result.slp = slp;
    if (alp != null) result.alp = alp;
    return result;
  }

  TokenType._();

  factory TokenType.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenType()..mergeFromBuffer(data, registry);
  factory TokenType.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenType()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, TokenType_TokenType>
      _TokenType_TokenTypeByTag = {
    1: TokenType_TokenType.slp,
    2: TokenType_TokenType.alp,
    0: TokenType_TokenType.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TokenType',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TokenType.$_createMessage)
    ..oo(0, [1, 2])
    ..aE<SlpTokenType>(1, _omitFieldNames ? '' : 'slp',
        enumValues: SlpTokenType.values)
    ..aE<AlpTokenType>(2, _omitFieldNames ? '' : 'alp',
        enumValues: AlpTokenType.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenType clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenType copyWith(void Function(TokenType) updates) =>
      super.copyWith((message) => updates(message as TokenType)) as TokenType;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TokenType() / TokenType.new instead')
  static TokenType create() => TokenType._();
  static $pb.GeneratedMessage $_createMessage() => TokenType._();
  @$core.override
  TokenType createEmptyInstance() => TokenType._();
  @$core.pragma('dart2js:noInline')
  static TokenType getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TokenType>(TokenType.$_createMessage);
  static TokenType? _defaultInstance;

  @$pb.TagNumber(1)
  @$pb.TagNumber(2)
  TokenType_TokenType whichTokenType() =>
      _TokenType_TokenTypeByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(1)
  @$pb.TagNumber(2)
  void clearTokenType() => $_clearField($_whichOneof(0));

  /// SLP token type. Can have unknown values for unknown token types
  @$pb.TagNumber(1)
  SlpTokenType get slp => $_getN(0);
  @$pb.TagNumber(1)
  set slp(SlpTokenType value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasSlp() => $_has(0);
  @$pb.TagNumber(1)
  void clearSlp() => $_clearField(1);

  /// ALP token type. Can have unknown values for unknown token types
  @$pb.TagNumber(2)
  AlpTokenType get alp => $_getN(1);
  @$pb.TagNumber(2)
  set alp(AlpTokenType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasAlp() => $_has(1);
  @$pb.TagNumber(2)
  void clearAlp() => $_clearField(2);
}

/// Info about a token
class TokenInfo extends $pb.GeneratedMessage {
  factory TokenInfo({
    $core.String? tokenId,
    TokenType? tokenType,
    GenesisInfo? genesisInfo,
    BlockMetadata? block,
    $fixnum.Int64? timeFirstSeen,
  }) {
    final result = TokenInfo._();
    if (tokenId != null) result.tokenId = tokenId;
    if (tokenType != null) result.tokenType = tokenType;
    if (genesisInfo != null) result.genesisInfo = genesisInfo;
    if (block != null) result.block = block;
    if (timeFirstSeen != null) result.timeFirstSeen = timeFirstSeen;
    return result;
  }

  TokenInfo._();

  factory TokenInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenInfo()..mergeFromBuffer(data, registry);
  factory TokenInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenInfo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TokenInfo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TokenInfo.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'tokenId')
    ..aOM<TokenType>(2, _omitFieldNames ? '' : 'tokenType',
        subBuilder: TokenType.$_createMessage)
    ..aOM<GenesisInfo>(3, _omitFieldNames ? '' : 'genesisInfo',
        subBuilder: GenesisInfo.$_createMessage)
    ..aOM<BlockMetadata>(4, _omitFieldNames ? '' : 'block',
        subBuilder: BlockMetadata.$_createMessage)
    ..aInt64(5, _omitFieldNames ? '' : 'timeFirstSeen')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenInfo copyWith(void Function(TokenInfo) updates) =>
      super.copyWith((message) => updates(message as TokenInfo)) as TokenInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TokenInfo() / TokenInfo.new instead')
  static TokenInfo create() => TokenInfo._();
  static $pb.GeneratedMessage $_createMessage() => TokenInfo._();
  @$core.override
  TokenInfo createEmptyInstance() => TokenInfo._();
  @$core.pragma('dart2js:noInline')
  static TokenInfo getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TokenInfo>(TokenInfo.$_createMessage);
  static TokenInfo? _defaultInstance;

  /// Hex token_id (in big-endian, like usually displayed to users) of the token.
  /// This is not `bytes` because SLP and ALP use different endiannnes, so to avoid this we use hex, which conventionally implies big-endian in a bitcoin context.
  @$pb.TagNumber(1)
  $core.String get tokenId => $_getSZ(0);
  @$pb.TagNumber(1)
  set tokenId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTokenId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTokenId() => $_clearField(1);

  /// Token type of the token
  @$pb.TagNumber(2)
  TokenType get tokenType => $_getN(1);
  @$pb.TagNumber(2)
  set tokenType(TokenType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasTokenType() => $_has(1);
  @$pb.TagNumber(2)
  void clearTokenType() => $_clearField(2);
  @$pb.TagNumber(2)
  TokenType ensureTokenType() => $_ensure(1);

  /// Info found in the token's GENESIS tx
  @$pb.TagNumber(3)
  GenesisInfo get genesisInfo => $_getN(2);
  @$pb.TagNumber(3)
  set genesisInfo(GenesisInfo value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasGenesisInfo() => $_has(2);
  @$pb.TagNumber(3)
  void clearGenesisInfo() => $_clearField(3);
  @$pb.TagNumber(3)
  GenesisInfo ensureGenesisInfo() => $_ensure(2);

  /// Block of the GENESIS tx, if it's mined already
  @$pb.TagNumber(4)
  BlockMetadata get block => $_getN(3);
  @$pb.TagNumber(4)
  set block(BlockMetadata value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasBlock() => $_has(3);
  @$pb.TagNumber(4)
  void clearBlock() => $_clearField(4);
  @$pb.TagNumber(4)
  BlockMetadata ensureBlock() => $_ensure(3);

  /// Time the GENESIS tx has first been seen by the indexer
  @$pb.TagNumber(5)
  $fixnum.Int64 get timeFirstSeen => $_getI64(4);
  @$pb.TagNumber(5)
  set timeFirstSeen($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasTimeFirstSeen() => $_has(4);
  @$pb.TagNumber(5)
  void clearTimeFirstSeen() => $_clearField(5);
}

/// Token involved in a transaction
class TokenEntry extends $pb.GeneratedMessage {
  factory TokenEntry({
    $core.String? tokenId,
    TokenType? tokenType,
    TokenTxType? txType,
    $core.String? groupTokenId,
    $core.bool? isInvalid,
    $core.String? burnSummary,
    $core.Iterable<TokenFailedColoring>? failedColorings,
    $core.String? actualBurnAtoms,
    $fixnum.Int64? intentionalBurnAtoms,
    $core.bool? burnsMintBatons,
  }) {
    final result = TokenEntry._();
    if (tokenId != null) result.tokenId = tokenId;
    if (tokenType != null) result.tokenType = tokenType;
    if (txType != null) result.txType = txType;
    if (groupTokenId != null) result.groupTokenId = groupTokenId;
    if (isInvalid != null) result.isInvalid = isInvalid;
    if (burnSummary != null) result.burnSummary = burnSummary;
    if (failedColorings != null) result.failedColorings.addAll(failedColorings);
    if (actualBurnAtoms != null) result.actualBurnAtoms = actualBurnAtoms;
    if (intentionalBurnAtoms != null)
      result.intentionalBurnAtoms = intentionalBurnAtoms;
    if (burnsMintBatons != null) result.burnsMintBatons = burnsMintBatons;
    return result;
  }

  TokenEntry._();

  factory TokenEntry.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenEntry()..mergeFromBuffer(data, registry);
  factory TokenEntry.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenEntry()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TokenEntry',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TokenEntry.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'tokenId')
    ..aOM<TokenType>(2, _omitFieldNames ? '' : 'tokenType',
        subBuilder: TokenType.$_createMessage)
    ..aE<TokenTxType>(3, _omitFieldNames ? '' : 'txType',
        enumValues: TokenTxType.values)
    ..aOS(4, _omitFieldNames ? '' : 'groupTokenId')
    ..aOB(5, _omitFieldNames ? '' : 'isInvalid')
    ..aOS(6, _omitFieldNames ? '' : 'burnSummary')
    ..pPM<TokenFailedColoring>(7, _omitFieldNames ? '' : 'failedColorings',
        subBuilder: TokenFailedColoring.$_createMessage)
    ..aOS(8, _omitFieldNames ? '' : 'actualBurnAtoms')
    ..a<$fixnum.Int64>(
        9, _omitFieldNames ? '' : 'intentionalBurnAtoms', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..aOB(10, _omitFieldNames ? '' : 'burnsMintBatons')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenEntry clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenEntry copyWith(void Function(TokenEntry) updates) =>
      super.copyWith((message) => updates(message as TokenEntry)) as TokenEntry;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TokenEntry() / TokenEntry.new instead')
  static TokenEntry create() => TokenEntry._();
  static $pb.GeneratedMessage $_createMessage() => TokenEntry._();
  @$core.override
  TokenEntry createEmptyInstance() => TokenEntry._();
  @$core.pragma('dart2js:noInline')
  static TokenEntry getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TokenEntry>(TokenEntry.$_createMessage);
  static TokenEntry? _defaultInstance;

  /// Hex token_id (in big-endian, like usually displayed to users) of the token.
  /// This is not `bytes` because SLP and ALP use different endiannes, so to avoid
  /// this we use hex, which conventionally implies big-endian in a bitcoin context.
  @$pb.TagNumber(1)
  $core.String get tokenId => $_getSZ(0);
  @$pb.TagNumber(1)
  set tokenId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTokenId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTokenId() => $_clearField(1);

  /// Token type of the token
  @$pb.TagNumber(2)
  TokenType get tokenType => $_getN(1);
  @$pb.TagNumber(2)
  set tokenType(TokenType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasTokenType() => $_has(1);
  @$pb.TagNumber(2)
  void clearTokenType() => $_clearField(2);
  @$pb.TagNumber(2)
  TokenType ensureTokenType() => $_ensure(1);

  /// Tx type of the token; NONE if there's no section that introduced it (e.g. in an accidental burn)
  @$pb.TagNumber(3)
  TokenTxType get txType => $_getN(2);
  @$pb.TagNumber(3)
  set txType(TokenTxType value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasTxType() => $_has(2);
  @$pb.TagNumber(3)
  void clearTxType() => $_clearField(3);

  /// For NFT1 Child tokens: group ID
  @$pb.TagNumber(4)
  $core.String get groupTokenId => $_getSZ(3);
  @$pb.TagNumber(4)
  set groupTokenId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasGroupTokenId() => $_has(3);
  @$pb.TagNumber(4)
  void clearGroupTokenId() => $_clearField(4);

  /// Whether the validation rules have been violated for this section
  @$pb.TagNumber(5)
  $core.bool get isInvalid => $_getBF(4);
  @$pb.TagNumber(5)
  set isInvalid($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(5)
  $core.bool hasIsInvalid() => $_has(4);
  @$pb.TagNumber(5)
  void clearIsInvalid() => $_clearField(5);

  /// Human-readable error message of why this entry burned tokens
  @$pb.TagNumber(6)
  $core.String get burnSummary => $_getSZ(5);
  @$pb.TagNumber(6)
  set burnSummary($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasBurnSummary() => $_has(5);
  @$pb.TagNumber(6)
  void clearBurnSummary() => $_clearField(6);

  /// Human-readable error messages of why colorings failed
  @$pb.TagNumber(7)
  $pb.PbList<TokenFailedColoring> get failedColorings => $_getList(6);

  /// Number of actually burned tokens (as decimal integer
  /// string, e.g. "2000"; in atoms aka base tokens).
  /// This is because burns can exceed the 64-bit range of
  /// values and protobuf doesn't have a nice type to encode this.
  @$pb.TagNumber(8)
  $core.String get actualBurnAtoms => $_getSZ(7);
  @$pb.TagNumber(8)
  set actualBurnAtoms($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasActualBurnAtoms() => $_has(7);
  @$pb.TagNumber(8)
  void clearActualBurnAtoms() => $_clearField(8);

  /// Burn amount (in atoms aka base tokens) the user explicitly opted into
  @$pb.TagNumber(9)
  $fixnum.Int64 get intentionalBurnAtoms => $_getI64(8);
  @$pb.TagNumber(9)
  set intentionalBurnAtoms($fixnum.Int64 value) => $_setInt64(8, value);
  @$pb.TagNumber(9)
  $core.bool hasIntentionalBurnAtoms() => $_has(8);
  @$pb.TagNumber(9)
  void clearIntentionalBurnAtoms() => $_clearField(9);

  /// Whether any mint batons have been burned of this token
  @$pb.TagNumber(10)
  $core.bool get burnsMintBatons => $_getBF(9);
  @$pb.TagNumber(10)
  set burnsMintBatons($core.bool value) => $_setBool(9, value);
  @$pb.TagNumber(10)
  $core.bool hasBurnsMintBatons() => $_has(9);
  @$pb.TagNumber(10)
  void clearBurnsMintBatons() => $_clearField(10);
}

/// Genesis info found in GENESIS txs of tokens
class GenesisInfo extends $pb.GeneratedMessage {
  factory GenesisInfo({
    $core.List<$core.int>? tokenTicker,
    $core.List<$core.int>? tokenName,
    $core.List<$core.int>? url,
    $core.List<$core.int>? hash,
    $core.List<$core.int>? mintVaultScripthash,
    $core.List<$core.int>? data,
    $core.List<$core.int>? authPubkey,
    $core.int? decimals,
  }) {
    final result = GenesisInfo._();
    if (tokenTicker != null) result.tokenTicker = tokenTicker;
    if (tokenName != null) result.tokenName = tokenName;
    if (url != null) result.url = url;
    if (hash != null) result.hash = hash;
    if (mintVaultScripthash != null)
      result.mintVaultScripthash = mintVaultScripthash;
    if (data != null) result.data = data;
    if (authPubkey != null) result.authPubkey = authPubkey;
    if (decimals != null) result.decimals = decimals;
    return result;
  }

  GenesisInfo._();

  factory GenesisInfo.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      GenesisInfo()..mergeFromBuffer(data, registry);
  factory GenesisInfo.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      GenesisInfo()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GenesisInfo',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: GenesisInfo.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'tokenTicker', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'tokenName', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        3, _omitFieldNames ? '' : 'url', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        4, _omitFieldNames ? '' : 'hash', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        5, _omitFieldNames ? '' : 'mintVaultScripthash', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        6, _omitFieldNames ? '' : 'data', $pb.PbFieldType.OY)
    ..a<$core.List<$core.int>>(
        7, _omitFieldNames ? '' : 'authPubkey', $pb.PbFieldType.OY)
    ..aI(8, _omitFieldNames ? '' : 'decimals', fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GenesisInfo clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GenesisInfo copyWith(void Function(GenesisInfo) updates) =>
      super.copyWith((message) => updates(message as GenesisInfo))
          as GenesisInfo;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use GenesisInfo() / GenesisInfo.new instead')
  static GenesisInfo create() => GenesisInfo._();
  static $pb.GeneratedMessage $_createMessage() => GenesisInfo._();
  @$core.override
  GenesisInfo createEmptyInstance() => GenesisInfo._();
  @$core.pragma('dart2js:noInline')
  static GenesisInfo getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GenesisInfo>(
          GenesisInfo.$_createMessage);
  static GenesisInfo? _defaultInstance;

  /// token_ticker of the token
  @$pb.TagNumber(1)
  $core.List<$core.int> get tokenTicker => $_getN(0);
  @$pb.TagNumber(1)
  set tokenTicker($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTokenTicker() => $_has(0);
  @$pb.TagNumber(1)
  void clearTokenTicker() => $_clearField(1);

  /// token_name of the token
  @$pb.TagNumber(2)
  $core.List<$core.int> get tokenName => $_getN(1);
  @$pb.TagNumber(2)
  set tokenName($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTokenName() => $_has(1);
  @$pb.TagNumber(2)
  void clearTokenName() => $_clearField(2);

  /// URL of the token
  @$pb.TagNumber(3)
  $core.List<$core.int> get url => $_getN(2);
  @$pb.TagNumber(3)
  set url($core.List<$core.int> value) => $_setBytes(2, value);
  @$pb.TagNumber(3)
  $core.bool hasUrl() => $_has(2);
  @$pb.TagNumber(3)
  void clearUrl() => $_clearField(3);

  /// token_document_hash of the token (only on SLP)
  @$pb.TagNumber(4)
  $core.List<$core.int> get hash => $_getN(3);
  @$pb.TagNumber(4)
  set hash($core.List<$core.int> value) => $_setBytes(3, value);
  @$pb.TagNumber(4)
  $core.bool hasHash() => $_has(3);
  @$pb.TagNumber(4)
  void clearHash() => $_clearField(4);

  /// mint_vault_scripthash (only on SLP V2 Mint Vault)
  @$pb.TagNumber(5)
  $core.List<$core.int> get mintVaultScripthash => $_getN(4);
  @$pb.TagNumber(5)
  set mintVaultScripthash($core.List<$core.int> value) => $_setBytes(4, value);
  @$pb.TagNumber(5)
  $core.bool hasMintVaultScripthash() => $_has(4);
  @$pb.TagNumber(5)
  void clearMintVaultScripthash() => $_clearField(5);

  /// Arbitray payload data of the token (only on ALP)
  @$pb.TagNumber(6)
  $core.List<$core.int> get data => $_getN(5);
  @$pb.TagNumber(6)
  set data($core.List<$core.int> value) => $_setBytes(5, value);
  @$pb.TagNumber(6)
  $core.bool hasData() => $_has(5);
  @$pb.TagNumber(6)
  void clearData() => $_clearField(6);

  /// auth_pubkey of the token (only on ALP)
  @$pb.TagNumber(7)
  $core.List<$core.int> get authPubkey => $_getN(6);
  @$pb.TagNumber(7)
  set authPubkey($core.List<$core.int> value) => $_setBytes(6, value);
  @$pb.TagNumber(7)
  $core.bool hasAuthPubkey() => $_has(6);
  @$pb.TagNumber(7)
  void clearAuthPubkey() => $_clearField(7);

  /// decimals of the token, i.e. how many decimal places the token should be displayed with.
  @$pb.TagNumber(8)
  $core.int get decimals => $_getIZ(7);
  @$pb.TagNumber(8)
  set decimals($core.int value) => $_setUnsignedInt32(7, value);
  @$pb.TagNumber(8)
  $core.bool hasDecimals() => $_has(7);
  @$pb.TagNumber(8)
  void clearDecimals() => $_clearField(8);
}

/// Token coloring an input or output
class Token extends $pb.GeneratedMessage {
  factory Token({
    $core.String? tokenId,
    TokenType? tokenType,
    $core.int? entryIdx,
    $fixnum.Int64? atoms,
    $core.bool? isMintBaton,
  }) {
    final result = Token._();
    if (tokenId != null) result.tokenId = tokenId;
    if (tokenType != null) result.tokenType = tokenType;
    if (entryIdx != null) result.entryIdx = entryIdx;
    if (atoms != null) result.atoms = atoms;
    if (isMintBaton != null) result.isMintBaton = isMintBaton;
    return result;
  }

  Token._();

  factory Token.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Token()..mergeFromBuffer(data, registry);
  factory Token.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Token()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Token',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Token.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'tokenId')
    ..aOM<TokenType>(2, _omitFieldNames ? '' : 'tokenType',
        subBuilder: TokenType.$_createMessage)
    ..aI(3, _omitFieldNames ? '' : 'entryIdx')
    ..a<$fixnum.Int64>(4, _omitFieldNames ? '' : 'atoms', $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..aOB(5, _omitFieldNames ? '' : 'isMintBaton')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Token clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Token copyWith(void Function(Token) updates) =>
      super.copyWith((message) => updates(message as Token)) as Token;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Token() / Token.new instead')
  static Token create() => Token._();
  static $pb.GeneratedMessage $_createMessage() => Token._();
  @$core.override
  Token createEmptyInstance() => Token._();
  @$core.pragma('dart2js:noInline')
  static Token getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Token>(Token.$_createMessage);
  static Token? _defaultInstance;

  /// Hex token_id of the token, see `TokenInfo` for details
  @$pb.TagNumber(1)
  $core.String get tokenId => $_getSZ(0);
  @$pb.TagNumber(1)
  set tokenId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTokenId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTokenId() => $_clearField(1);

  /// Token type of the token
  @$pb.TagNumber(2)
  TokenType get tokenType => $_getN(1);
  @$pb.TagNumber(2)
  set tokenType(TokenType value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasTokenType() => $_has(1);
  @$pb.TagNumber(2)
  void clearTokenType() => $_clearField(2);
  @$pb.TagNumber(2)
  TokenType ensureTokenType() => $_ensure(1);

  /// Index into `token_entries` for `Tx`. -1 for UTXOs
  @$pb.TagNumber(3)
  $core.int get entryIdx => $_getIZ(2);
  @$pb.TagNumber(3)
  set entryIdx($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasEntryIdx() => $_has(2);
  @$pb.TagNumber(3)
  void clearEntryIdx() => $_clearField(3);

  /// Base token amount of the input/output
  @$pb.TagNumber(4)
  $fixnum.Int64 get atoms => $_getI64(3);
  @$pb.TagNumber(4)
  set atoms($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasAtoms() => $_has(3);
  @$pb.TagNumber(4)
  void clearAtoms() => $_clearField(4);

  /// Whether the token is a mint baton
  @$pb.TagNumber(5)
  $core.bool get isMintBaton => $_getBF(4);
  @$pb.TagNumber(5)
  set isMintBaton($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(5)
  $core.bool hasIsMintBaton() => $_has(4);
  @$pb.TagNumber(5)
  void clearIsMintBaton() => $_clearField(5);
}

/// A report of a failed parsing attempt of SLP/ALP.
/// This should always indicate something went wrong when building the tx.
class TokenFailedParsing extends $pb.GeneratedMessage {
  factory TokenFailedParsing({
    $core.int? pushdataIdx,
    $core.List<$core.int>? bytes,
    $core.String? error,
  }) {
    final result = TokenFailedParsing._();
    if (pushdataIdx != null) result.pushdataIdx = pushdataIdx;
    if (bytes != null) result.bytes = bytes;
    if (error != null) result.error = error;
    return result;
  }

  TokenFailedParsing._();

  factory TokenFailedParsing.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenFailedParsing()..mergeFromBuffer(data, registry);
  factory TokenFailedParsing.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenFailedParsing()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TokenFailedParsing',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TokenFailedParsing.$_createMessage)
    ..aI(1, _omitFieldNames ? '' : 'pushdataIdx')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'bytes', $pb.PbFieldType.OY)
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenFailedParsing clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenFailedParsing copyWith(void Function(TokenFailedParsing) updates) =>
      super.copyWith((message) => updates(message as TokenFailedParsing))
          as TokenFailedParsing;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TokenFailedParsing() / TokenFailedParsing.new instead')
  static TokenFailedParsing create() => TokenFailedParsing._();
  static $pb.GeneratedMessage $_createMessage() => TokenFailedParsing._();
  @$core.override
  TokenFailedParsing createEmptyInstance() => TokenFailedParsing._();
  @$core.pragma('dart2js:noInline')
  static TokenFailedParsing getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TokenFailedParsing>(
          TokenFailedParsing.$_createMessage);
  static TokenFailedParsing? _defaultInstance;

  /// For ALP, the index of the pushdata in the OP_RETURN that failed parsing.
  /// -1 if the whole OP_RETURN failed, e.g. for SLP or eMPP
  @$pb.TagNumber(1)
  $core.int get pushdataIdx => $_getIZ(0);
  @$pb.TagNumber(1)
  set pushdataIdx($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPushdataIdx() => $_has(0);
  @$pb.TagNumber(1)
  void clearPushdataIdx() => $_clearField(1);

  /// The bytes that failed parsing, useful for debugging
  @$pb.TagNumber(2)
  $core.List<$core.int> get bytes => $_getN(1);
  @$pb.TagNumber(2)
  set bytes($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasBytes() => $_has(1);
  @$pb.TagNumber(2)
  void clearBytes() => $_clearField(2);

  /// Human-readable message of what went wrong
  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(2);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(2);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// A report of a failed coloring attempt of SLP/ALP.
/// This should always indicate something went wrong when building the tx.
class TokenFailedColoring extends $pb.GeneratedMessage {
  factory TokenFailedColoring({
    $core.int? pushdataIdx,
    $core.String? error,
  }) {
    final result = TokenFailedColoring._();
    if (pushdataIdx != null) result.pushdataIdx = pushdataIdx;
    if (error != null) result.error = error;
    return result;
  }

  TokenFailedColoring._();

  factory TokenFailedColoring.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenFailedColoring()..mergeFromBuffer(data, registry);
  factory TokenFailedColoring.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TokenFailedColoring()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TokenFailedColoring',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TokenFailedColoring.$_createMessage)
    ..aI(1, _omitFieldNames ? '' : 'pushdataIdx')
    ..aOS(3, _omitFieldNames ? '' : 'error')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenFailedColoring clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TokenFailedColoring copyWith(void Function(TokenFailedColoring) updates) =>
      super.copyWith((message) => updates(message as TokenFailedColoring))
          as TokenFailedColoring;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core
      .Deprecated('Use TokenFailedColoring() / TokenFailedColoring.new instead')
  static TokenFailedColoring create() => TokenFailedColoring._();
  static $pb.GeneratedMessage $_createMessage() => TokenFailedColoring._();
  @$core.override
  TokenFailedColoring createEmptyInstance() => TokenFailedColoring._();
  @$core.pragma('dart2js:noInline')
  static TokenFailedColoring getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TokenFailedColoring>(
          TokenFailedColoring.$_createMessage);
  static TokenFailedColoring? _defaultInstance;

  /// For ALP, the index of the pushdata in the OP_RETURN that failed parsing.
  @$pb.TagNumber(1)
  $core.int get pushdataIdx => $_getIZ(0);
  @$pb.TagNumber(1)
  set pushdataIdx($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPushdataIdx() => $_has(0);
  @$pb.TagNumber(1)
  void clearPushdataIdx() => $_clearField(1);

  /// Human-readable message of what went wrong
  @$pb.TagNumber(3)
  $core.String get error => $_getSZ(1);
  @$pb.TagNumber(3)
  set error($core.String value) => $_setString(1, value);
  @$pb.TagNumber(3)
  $core.bool hasError() => $_has(1);
  @$pb.TagNumber(3)
  void clearError() => $_clearField(3);
}

/// Data attached by a plugin to an output
class PluginEntry extends $pb.GeneratedMessage {
  factory PluginEntry({
    $core.Iterable<$core.List<$core.int>>? groups,
    $core.Iterable<$core.List<$core.int>>? data,
  }) {
    final result = PluginEntry._();
    if (groups != null) result.groups.addAll(groups);
    if (data != null) result.data.addAll(data);
    return result;
  }

  PluginEntry._();

  factory PluginEntry.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginEntry()..mergeFromBuffer(data, registry);
  factory PluginEntry.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginEntry()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'PluginEntry',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: PluginEntry.$_createMessage)
    ..p<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'groups', $pb.PbFieldType.PY)
    ..p<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'data', $pb.PbFieldType.PY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginEntry clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginEntry copyWith(void Function(PluginEntry) updates) =>
      super.copyWith((message) => updates(message as PluginEntry))
          as PluginEntry;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use PluginEntry() / PluginEntry.new instead')
  static PluginEntry create() => PluginEntry._();
  static $pb.GeneratedMessage $_createMessage() => PluginEntry._();
  @$core.override
  PluginEntry createEmptyInstance() => PluginEntry._();
  @$core.pragma('dart2js:noInline')
  static PluginEntry getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<PluginEntry>(
          PluginEntry.$_createMessage);
  static PluginEntry? _defaultInstance;

  /// Groups assigned to this output
  @$pb.TagNumber(1)
  $pb.PbList<$core.List<$core.int>> get groups => $_getList(0);

  /// Data assigned to the output
  @$pb.TagNumber(2)
  $pb.PbList<$core.List<$core.int>> get data => $_getList(1);
}

/// Data about a plugin group
class PluginGroup extends $pb.GeneratedMessage {
  factory PluginGroup({
    $core.List<$core.int>? group,
  }) {
    final result = PluginGroup._();
    if (group != null) result.group = group;
    return result;
  }

  PluginGroup._();

  factory PluginGroup.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginGroup()..mergeFromBuffer(data, registry);
  factory PluginGroup.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginGroup()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'PluginGroup',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: PluginGroup.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'group', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginGroup clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginGroup copyWith(void Function(PluginGroup) updates) =>
      super.copyWith((message) => updates(message as PluginGroup))
          as PluginGroup;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use PluginGroup() / PluginGroup.new instead')
  static PluginGroup create() => PluginGroup._();
  static $pb.GeneratedMessage $_createMessage() => PluginGroup._();
  @$core.override
  PluginGroup createEmptyInstance() => PluginGroup._();
  @$core.pragma('dart2js:noInline')
  static PluginGroup getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<PluginGroup>(
          PluginGroup.$_createMessage);
  static PluginGroup? _defaultInstance;

  /// Group bytes
  @$pb.TagNumber(1)
  $core.List<$core.int> get group => $_getN(0);
  @$pb.TagNumber(1)
  set group($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasGroup() => $_has(0);
  @$pb.TagNumber(1)
  void clearGroup() => $_clearField(1);
}

/// List of plugin groups
class PluginGroups extends $pb.GeneratedMessage {
  factory PluginGroups({
    $core.Iterable<PluginGroup>? groups,
    $core.List<$core.int>? nextStart,
  }) {
    final result = PluginGroups._();
    if (groups != null) result.groups.addAll(groups);
    if (nextStart != null) result.nextStart = nextStart;
    return result;
  }

  PluginGroups._();

  factory PluginGroups.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginGroups()..mergeFromBuffer(data, registry);
  factory PluginGroups.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      PluginGroups()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'PluginGroups',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: PluginGroups.$_createMessage)
    ..pPM<PluginGroup>(1, _omitFieldNames ? '' : 'groups',
        subBuilder: PluginGroup.$_createMessage)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'nextStart', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginGroups clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  PluginGroups copyWith(void Function(PluginGroups) updates) =>
      super.copyWith((message) => updates(message as PluginGroups))
          as PluginGroups;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use PluginGroups() / PluginGroups.new instead')
  static PluginGroups create() => PluginGroups._();
  static $pb.GeneratedMessage $_createMessage() => PluginGroups._();
  @$core.override
  PluginGroups createEmptyInstance() => PluginGroups._();
  @$core.pragma('dart2js:noInline')
  static PluginGroups getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<PluginGroups>(
          PluginGroups.$_createMessage);
  static PluginGroups? _defaultInstance;

  /// Groups
  @$pb.TagNumber(1)
  $pb.PbList<PluginGroup> get groups => $_getList(0);

  /// Group that if specified as `start` will give us the next groups,
  /// or empty if groups have been exausted.
  @$pb.TagNumber(2)
  $core.List<$core.int> get nextStart => $_getN(1);
  @$pb.TagNumber(2)
  set nextStart($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasNextStart() => $_has(1);
  @$pb.TagNumber(2)
  void clearNextStart() => $_clearField(2);
}

/// Page with txs
class TxHistoryPage extends $pb.GeneratedMessage {
  factory TxHistoryPage({
    $core.Iterable<Tx>? txs,
    $core.int? numPages,
    $core.int? numTxs,
  }) {
    final result = TxHistoryPage._();
    if (txs != null) result.txs.addAll(txs);
    if (numPages != null) result.numPages = numPages;
    if (numTxs != null) result.numTxs = numTxs;
    return result;
  }

  TxHistoryPage._();

  factory TxHistoryPage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxHistoryPage()..mergeFromBuffer(data, registry);
  factory TxHistoryPage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxHistoryPage()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TxHistoryPage',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TxHistoryPage.$_createMessage)
    ..pPM<Tx>(1, _omitFieldNames ? '' : 'txs', subBuilder: Tx.$_createMessage)
    ..aI(2, _omitFieldNames ? '' : 'numPages', fieldType: $pb.PbFieldType.OU3)
    ..aI(3, _omitFieldNames ? '' : 'numTxs', fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxHistoryPage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxHistoryPage copyWith(void Function(TxHistoryPage) updates) =>
      super.copyWith((message) => updates(message as TxHistoryPage))
          as TxHistoryPage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use TxHistoryPage() / TxHistoryPage.new instead')
  static TxHistoryPage create() => TxHistoryPage._();
  static $pb.GeneratedMessage $_createMessage() => TxHistoryPage._();
  @$core.override
  TxHistoryPage createEmptyInstance() => TxHistoryPage._();
  @$core.pragma('dart2js:noInline')
  static TxHistoryPage getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TxHistoryPage>(
          TxHistoryPage.$_createMessage);
  static TxHistoryPage? _defaultInstance;

  /// Txs of the page
  @$pb.TagNumber(1)
  $pb.PbList<Tx> get txs => $_getList(0);

  /// How many pages there are total
  @$pb.TagNumber(2)
  $core.int get numPages => $_getIZ(1);
  @$pb.TagNumber(2)
  set numPages($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasNumPages() => $_has(1);
  @$pb.TagNumber(2)
  void clearNumPages() => $_clearField(2);

  /// How many txs there are total
  @$pb.TagNumber(3)
  $core.int get numTxs => $_getIZ(2);
  @$pb.TagNumber(3)
  set numTxs($core.int value) => $_setUnsignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasNumTxs() => $_has(2);
  @$pb.TagNumber(3)
  void clearNumTxs() => $_clearField(3);
}

/// List of UTXOs of a script
class ScriptUtxos extends $pb.GeneratedMessage {
  factory ScriptUtxos({
    $core.List<$core.int>? script,
    $core.Iterable<ScriptUtxo>? utxos,
  }) {
    final result = ScriptUtxos._();
    if (script != null) result.script = script;
    if (utxos != null) result.utxos.addAll(utxos);
    return result;
  }

  ScriptUtxos._();

  factory ScriptUtxos.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptUtxos()..mergeFromBuffer(data, registry);
  factory ScriptUtxos.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptUtxos()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptUtxos',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptUtxos.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'script', $pb.PbFieldType.OY)
    ..pPM<ScriptUtxo>(2, _omitFieldNames ? '' : 'utxos',
        subBuilder: ScriptUtxo.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptUtxos clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptUtxos copyWith(void Function(ScriptUtxos) updates) =>
      super.copyWith((message) => updates(message as ScriptUtxos))
          as ScriptUtxos;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use ScriptUtxos() / ScriptUtxos.new instead')
  static ScriptUtxos create() => ScriptUtxos._();
  static $pb.GeneratedMessage $_createMessage() => ScriptUtxos._();
  @$core.override
  ScriptUtxos createEmptyInstance() => ScriptUtxos._();
  @$core.pragma('dart2js:noInline')
  static ScriptUtxos getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ScriptUtxos>(
          ScriptUtxos.$_createMessage);
  static ScriptUtxos? _defaultInstance;

  /// The serialized script of the UTXOs
  @$pb.TagNumber(1)
  $core.List<$core.int> get script => $_getN(0);
  @$pb.TagNumber(1)
  set script($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasScript() => $_has(0);
  @$pb.TagNumber(1)
  void clearScript() => $_clearField(1);

  /// UTXOs of the script.
  @$pb.TagNumber(2)
  $pb.PbList<ScriptUtxo> get utxos => $_getList(1);
}

/// Script identity by type and payload. Same field layout as `WsSubScript`.
class ScriptRef extends $pb.GeneratedMessage {
  factory ScriptRef({
    $core.String? scriptType,
    $core.List<$core.int>? payload,
  }) {
    final result = ScriptRef._();
    if (scriptType != null) result.scriptType = scriptType;
    if (payload != null) result.payload = payload;
    return result;
  }

  ScriptRef._();

  factory ScriptRef.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptRef()..mergeFromBuffer(data, registry);
  factory ScriptRef.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptRef()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptRef',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptRef.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'scriptType')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'payload', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptRef clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptRef copyWith(void Function(ScriptRef) updates) =>
      super.copyWith((message) => updates(message as ScriptRef)) as ScriptRef;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use ScriptRef() / ScriptRef.new instead')
  static ScriptRef create() => ScriptRef._();
  static $pb.GeneratedMessage $_createMessage() => ScriptRef._();
  @$core.override
  ScriptRef createEmptyInstance() => ScriptRef._();
  @$core.pragma('dart2js:noInline')
  static ScriptRef getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptRef>(ScriptRef.$_createMessage);
  static ScriptRef? _defaultInstance;

  /// Script type to subscribe to ("p2pkh", "p2sh", "p2pk", "other").
  @$pb.TagNumber(1)
  $core.String get scriptType => $_getSZ(0);
  @$pb.TagNumber(1)
  set scriptType($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasScriptType() => $_has(0);
  @$pb.TagNumber(1)
  void clearScriptType() => $_clearField(1);

  /// Payload for the given script type:
  /// - 20-byte hash for "p2pkh" and "p2sh"
  /// - 33-byte or 65-byte pubkey for "p2pk"
  /// - Serialized script for "other"
  @$pb.TagNumber(2)
  $core.List<$core.int> get payload => $_getN(1);
  @$pb.TagNumber(2)
  set payload($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPayload() => $_has(1);
  @$pb.TagNumber(2)
  void clearPayload() => $_clearField(2);
}

/// Parameters for requesting the utxos for a batch of scripts.
class ScriptBatchUtxosParams extends $pb.GeneratedMessage {
  factory ScriptBatchUtxosParams({
    $core.Iterable<ScriptRef>? scripts,
  }) {
    final result = ScriptBatchUtxosParams._();
    if (scripts != null) result.scripts.addAll(scripts);
    return result;
  }

  ScriptBatchUtxosParams._();

  factory ScriptBatchUtxosParams.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosParams()..mergeFromBuffer(data, registry);
  factory ScriptBatchUtxosParams.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosParams()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchUtxosParams',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchUtxosParams.$_createMessage)
    ..pPM<ScriptRef>(1, _omitFieldNames ? '' : 'scripts',
        subBuilder: ScriptRef.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosParams clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosParams copyWith(
          void Function(ScriptBatchUtxosParams) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchUtxosParams))
          as ScriptBatchUtxosParams;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchUtxosParams() / ScriptBatchUtxosParams.new instead')
  static ScriptBatchUtxosParams create() => ScriptBatchUtxosParams._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchUtxosParams._();
  @$core.override
  ScriptBatchUtxosParams createEmptyInstance() => ScriptBatchUtxosParams._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchUtxosParams getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchUtxosParams>(
          ScriptBatchUtxosParams.$_createMessage);
  static ScriptBatchUtxosParams? _defaultInstance;

  /// Scripts to query.
  @$pb.TagNumber(1)
  $pb.PbList<ScriptRef> get scripts => $_getList(0);
}

/// Request the utxos for a batch of scripts.
class ScriptBatchUtxosRequest extends $pb.GeneratedMessage {
  factory ScriptBatchUtxosRequest({
    ScriptBatchUtxosParams? params,
  }) {
    final result = ScriptBatchUtxosRequest._();
    if (params != null) result.params = params;
    return result;
  }

  ScriptBatchUtxosRequest._();

  factory ScriptBatchUtxosRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosRequest()..mergeFromBuffer(data, registry);
  factory ScriptBatchUtxosRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosRequest()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchUtxosRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchUtxosRequest.$_createMessage)
    ..aOM<ScriptBatchUtxosParams>(1, _omitFieldNames ? '' : 'params',
        subBuilder: ScriptBatchUtxosParams.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosRequest copyWith(
          void Function(ScriptBatchUtxosRequest) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchUtxosRequest))
          as ScriptBatchUtxosRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchUtxosRequest() / ScriptBatchUtxosRequest.new instead')
  static ScriptBatchUtxosRequest create() => ScriptBatchUtxosRequest._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchUtxosRequest._();
  @$core.override
  ScriptBatchUtxosRequest createEmptyInstance() => ScriptBatchUtxosRequest._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchUtxosRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchUtxosRequest>(
          ScriptBatchUtxosRequest.$_createMessage);
  static ScriptBatchUtxosRequest? _defaultInstance;

  /// Batch inputs (scripts to resolve UTXOs for).
  @$pb.TagNumber(1)
  ScriptBatchUtxosParams get params => $_getN(0);
  @$pb.TagNumber(1)
  set params(ScriptBatchUtxosParams value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasParams() => $_has(0);
  @$pb.TagNumber(1)
  void clearParams() => $_clearField(1);
  @$pb.TagNumber(1)
  ScriptBatchUtxosParams ensureParams() => $_ensure(0);
}

/// One row in the batch response (echoes the request script from the same index).
class ScriptBatchUtxosRow extends $pb.GeneratedMessage {
  factory ScriptBatchUtxosRow({
    ScriptRef? script,
    ScriptUtxos? utxos,
  }) {
    final result = ScriptBatchUtxosRow._();
    if (script != null) result.script = script;
    if (utxos != null) result.utxos = utxos;
    return result;
  }

  ScriptBatchUtxosRow._();

  factory ScriptBatchUtxosRow.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosRow()..mergeFromBuffer(data, registry);
  factory ScriptBatchUtxosRow.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosRow()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchUtxosRow',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchUtxosRow.$_createMessage)
    ..aOM<ScriptRef>(1, _omitFieldNames ? '' : 'script',
        subBuilder: ScriptRef.$_createMessage)
    ..aOM<ScriptUtxos>(2, _omitFieldNames ? '' : 'utxos',
        subBuilder: ScriptUtxos.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosRow clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosRow copyWith(void Function(ScriptBatchUtxosRow) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchUtxosRow))
          as ScriptBatchUtxosRow;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core
      .Deprecated('Use ScriptBatchUtxosRow() / ScriptBatchUtxosRow.new instead')
  static ScriptBatchUtxosRow create() => ScriptBatchUtxosRow._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchUtxosRow._();
  @$core.override
  ScriptBatchUtxosRow createEmptyInstance() => ScriptBatchUtxosRow._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchUtxosRow getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchUtxosRow>(
          ScriptBatchUtxosRow.$_createMessage);
  static ScriptBatchUtxosRow? _defaultInstance;

  /// The requested script.
  @$pb.TagNumber(1)
  ScriptRef get script => $_getN(0);
  @$pb.TagNumber(1)
  set script(ScriptRef value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasScript() => $_has(0);
  @$pb.TagNumber(1)
  void clearScript() => $_clearField(1);
  @$pb.TagNumber(1)
  ScriptRef ensureScript() => $_ensure(0);

  /// UTXO set for this script.
  @$pb.TagNumber(2)
  ScriptUtxos get utxos => $_getN(1);
  @$pb.TagNumber(2)
  set utxos(ScriptUtxos value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasUtxos() => $_has(1);
  @$pb.TagNumber(2)
  void clearUtxos() => $_clearField(2);
  @$pb.TagNumber(2)
  ScriptUtxos ensureUtxos() => $_ensure(1);
}

/// The utxos from a batch of scripts.
class ScriptBatchUtxosResponse extends $pb.GeneratedMessage {
  factory ScriptBatchUtxosResponse({
    $core.Iterable<ScriptBatchUtxosRow>? rows,
  }) {
    final result = ScriptBatchUtxosResponse._();
    if (rows != null) result.rows.addAll(rows);
    return result;
  }

  ScriptBatchUtxosResponse._();

  factory ScriptBatchUtxosResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosResponse()..mergeFromBuffer(data, registry);
  factory ScriptBatchUtxosResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchUtxosResponse()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchUtxosResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchUtxosResponse.$_createMessage)
    ..pPM<ScriptBatchUtxosRow>(1, _omitFieldNames ? '' : 'rows',
        subBuilder: ScriptBatchUtxosRow.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchUtxosResponse copyWith(
          void Function(ScriptBatchUtxosResponse) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchUtxosResponse))
          as ScriptBatchUtxosResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchUtxosResponse() / ScriptBatchUtxosResponse.new instead')
  static ScriptBatchUtxosResponse create() => ScriptBatchUtxosResponse._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchUtxosResponse._();
  @$core.override
  ScriptBatchUtxosResponse createEmptyInstance() =>
      ScriptBatchUtxosResponse._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchUtxosResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchUtxosResponse>(
          ScriptBatchUtxosResponse.$_createMessage);
  static ScriptBatchUtxosResponse? _defaultInstance;

  /// One row per requested script, same order as `ScriptBatchUtxosParams.scripts`.
  @$pb.TagNumber(1)
  $pb.PbList<ScriptBatchUtxosRow> get rows => $_getList(0);
}

/// Parameters for batch script summary (same shape as `ScriptBatchUtxosParams`).
class ScriptBatchSummaryParams extends $pb.GeneratedMessage {
  factory ScriptBatchSummaryParams({
    $core.Iterable<ScriptRef>? scripts,
  }) {
    final result = ScriptBatchSummaryParams._();
    if (scripts != null) result.scripts.addAll(scripts);
    return result;
  }

  ScriptBatchSummaryParams._();

  factory ScriptBatchSummaryParams.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryParams()..mergeFromBuffer(data, registry);
  factory ScriptBatchSummaryParams.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryParams()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchSummaryParams',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchSummaryParams.$_createMessage)
    ..pPM<ScriptRef>(1, _omitFieldNames ? '' : 'scripts',
        subBuilder: ScriptRef.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryParams clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryParams copyWith(
          void Function(ScriptBatchSummaryParams) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchSummaryParams))
          as ScriptBatchSummaryParams;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchSummaryParams() / ScriptBatchSummaryParams.new instead')
  static ScriptBatchSummaryParams create() => ScriptBatchSummaryParams._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchSummaryParams._();
  @$core.override
  ScriptBatchSummaryParams createEmptyInstance() =>
      ScriptBatchSummaryParams._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchSummaryParams getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchSummaryParams>(
          ScriptBatchSummaryParams.$_createMessage);
  static ScriptBatchSummaryParams? _defaultInstance;

  /// Scripts to query.
  @$pb.TagNumber(1)
  $pb.PbList<ScriptRef> get scripts => $_getList(0);
}

/// Request a batch script summary for scripts.
class ScriptBatchSummaryRequest extends $pb.GeneratedMessage {
  factory ScriptBatchSummaryRequest({
    ScriptBatchSummaryParams? params,
  }) {
    final result = ScriptBatchSummaryRequest._();
    if (params != null) result.params = params;
    return result;
  }

  ScriptBatchSummaryRequest._();

  factory ScriptBatchSummaryRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryRequest()..mergeFromBuffer(data, registry);
  factory ScriptBatchSummaryRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryRequest()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchSummaryRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchSummaryRequest.$_createMessage)
    ..aOM<ScriptBatchSummaryParams>(1, _omitFieldNames ? '' : 'params',
        subBuilder: ScriptBatchSummaryParams.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryRequest copyWith(
          void Function(ScriptBatchSummaryRequest) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchSummaryRequest))
          as ScriptBatchSummaryRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchSummaryRequest() / ScriptBatchSummaryRequest.new instead')
  static ScriptBatchSummaryRequest create() => ScriptBatchSummaryRequest._();
  static $pb.GeneratedMessage $_createMessage() =>
      ScriptBatchSummaryRequest._();
  @$core.override
  ScriptBatchSummaryRequest createEmptyInstance() =>
      ScriptBatchSummaryRequest._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchSummaryRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchSummaryRequest>(
          ScriptBatchSummaryRequest.$_createMessage);
  static ScriptBatchSummaryRequest? _defaultInstance;

  /// Batch inputs (scripts to resolve summaries for).
  @$pb.TagNumber(1)
  ScriptBatchSummaryParams get params => $_getN(0);
  @$pb.TagNumber(1)
  set params(ScriptBatchSummaryParams value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasParams() => $_has(0);
  @$pb.TagNumber(1)
  void clearParams() => $_clearField(1);
  @$pb.TagNumber(1)
  ScriptBatchSummaryParams ensureParams() => $_ensure(0);
}

/// One row in the batch script summary response.
class ScriptBatchSummaryRow extends $pb.GeneratedMessage {
  factory ScriptBatchSummaryRow({
    ScriptRef? script,
    $core.int? numTxs,
    $core.int? numUtxos,
    Tx? latestTx,
  }) {
    final result = ScriptBatchSummaryRow._();
    if (script != null) result.script = script;
    if (numTxs != null) result.numTxs = numTxs;
    if (numUtxos != null) result.numUtxos = numUtxos;
    if (latestTx != null) result.latestTx = latestTx;
    return result;
  }

  ScriptBatchSummaryRow._();

  factory ScriptBatchSummaryRow.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryRow()..mergeFromBuffer(data, registry);
  factory ScriptBatchSummaryRow.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryRow()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchSummaryRow',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchSummaryRow.$_createMessage)
    ..aOM<ScriptRef>(1, _omitFieldNames ? '' : 'script',
        subBuilder: ScriptRef.$_createMessage)
    ..aI(2, _omitFieldNames ? '' : 'numTxs', fieldType: $pb.PbFieldType.OU3)
    ..aI(3, _omitFieldNames ? '' : 'numUtxos', fieldType: $pb.PbFieldType.OU3)
    ..aOM<Tx>(4, _omitFieldNames ? '' : 'latestTx',
        subBuilder: Tx.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryRow clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryRow copyWith(
          void Function(ScriptBatchSummaryRow) updates) =>
      super.copyWith((message) => updates(message as ScriptBatchSummaryRow))
          as ScriptBatchSummaryRow;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchSummaryRow() / ScriptBatchSummaryRow.new instead')
  static ScriptBatchSummaryRow create() => ScriptBatchSummaryRow._();
  static $pb.GeneratedMessage $_createMessage() => ScriptBatchSummaryRow._();
  @$core.override
  ScriptBatchSummaryRow createEmptyInstance() => ScriptBatchSummaryRow._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchSummaryRow getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchSummaryRow>(
          ScriptBatchSummaryRow.$_createMessage);
  static ScriptBatchSummaryRow? _defaultInstance;

  /// The requested script.
  @$pb.TagNumber(1)
  ScriptRef get script => $_getN(0);
  @$pb.TagNumber(1)
  set script(ScriptRef value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasScript() => $_has(0);
  @$pb.TagNumber(1)
  void clearScript() => $_clearField(1);
  @$pb.TagNumber(1)
  ScriptRef ensureScript() => $_ensure(0);

  /// Total txs touching this script (confirmed index + mempool), same as
  /// `TxHistoryPage.num_txs` for `/history`.
  @$pb.TagNumber(2)
  $core.int get numTxs => $_getIZ(1);
  @$pb.TagNumber(2)
  set numTxs($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasNumTxs() => $_has(1);
  @$pb.TagNumber(2)
  void clearNumTxs() => $_clearField(2);

  /// Number of UTXOs for this script (confirmed + mempool), same as
  /// `len(script().utxos().utxos)`.
  @$pb.TagNumber(3)
  $core.int get numUtxos => $_getIZ(2);
  @$pb.TagNumber(3)
  set numUtxos($core.int value) => $_setUnsignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasNumUtxos() => $_has(2);
  @$pb.TagNumber(3)
  void clearNumUtxos() => $_clearField(3);

  /// Most recent tx in `history` order when `num_txs > 0`; unset when
  /// `num_txs == 0`.
  @$pb.TagNumber(4)
  Tx get latestTx => $_getN(3);
  @$pb.TagNumber(4)
  set latestTx(Tx value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasLatestTx() => $_has(3);
  @$pb.TagNumber(4)
  void clearLatestTx() => $_clearField(4);
  @$pb.TagNumber(4)
  Tx ensureLatestTx() => $_ensure(3);
}

/// Response for `POST /script/batch/summary`.
class ScriptBatchSummaryResponse extends $pb.GeneratedMessage {
  factory ScriptBatchSummaryResponse({
    $core.Iterable<ScriptBatchSummaryRow>? rows,
  }) {
    final result = ScriptBatchSummaryResponse._();
    if (rows != null) result.rows.addAll(rows);
    return result;
  }

  ScriptBatchSummaryResponse._();

  factory ScriptBatchSummaryResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryResponse()..mergeFromBuffer(data, registry);
  factory ScriptBatchSummaryResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      ScriptBatchSummaryResponse()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ScriptBatchSummaryResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: ScriptBatchSummaryResponse.$_createMessage)
    ..pPM<ScriptBatchSummaryRow>(1, _omitFieldNames ? '' : 'rows',
        subBuilder: ScriptBatchSummaryRow.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ScriptBatchSummaryResponse copyWith(
          void Function(ScriptBatchSummaryResponse) updates) =>
      super.copyWith(
              (message) => updates(message as ScriptBatchSummaryResponse))
          as ScriptBatchSummaryResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use ScriptBatchSummaryResponse() / ScriptBatchSummaryResponse.new instead')
  static ScriptBatchSummaryResponse create() => ScriptBatchSummaryResponse._();
  static $pb.GeneratedMessage $_createMessage() =>
      ScriptBatchSummaryResponse._();
  @$core.override
  ScriptBatchSummaryResponse createEmptyInstance() =>
      ScriptBatchSummaryResponse._();
  @$core.pragma('dart2js:noInline')
  static ScriptBatchSummaryResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ScriptBatchSummaryResponse>(
          ScriptBatchSummaryResponse.$_createMessage);
  static ScriptBatchSummaryResponse? _defaultInstance;

  /// One row per requested script, same order as `ScriptBatchSummaryParams.scripts`.
  @$pb.TagNumber(1)
  $pb.PbList<ScriptBatchSummaryRow> get rows => $_getList(0);
}

/// List of UTXOs
class Utxos extends $pb.GeneratedMessage {
  factory Utxos({
    $core.Iterable<Utxo>? utxos,
  }) {
    final result = Utxos._();
    if (utxos != null) result.utxos.addAll(utxos);
    return result;
  }

  Utxos._();

  factory Utxos.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Utxos()..mergeFromBuffer(data, registry);
  factory Utxos.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Utxos()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Utxos',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Utxos.$_createMessage)
    ..pPM<Utxo>(1, _omitFieldNames ? '' : 'utxos',
        subBuilder: Utxo.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Utxos clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Utxos copyWith(void Function(Utxos) updates) =>
      super.copyWith((message) => updates(message as Utxos)) as Utxos;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Utxos() / Utxos.new instead')
  static Utxos create() => Utxos._();
  static $pb.GeneratedMessage $_createMessage() => Utxos._();
  @$core.override
  Utxos createEmptyInstance() => Utxos._();
  @$core.pragma('dart2js:noInline')
  static Utxos getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Utxos>(Utxos.$_createMessage);
  static Utxos? _defaultInstance;

  /// UTXOs
  @$pb.TagNumber(1)
  $pb.PbList<Utxo> get utxos => $_getList(0);
}

/// Broadcast a single tx
class BroadcastTxRequest extends $pb.GeneratedMessage {
  factory BroadcastTxRequest({
    $core.List<$core.int>? rawTx,
    $core.bool? skipTokenChecks,
    $fixnum.Int64? finalizationTimeoutSecs,
  }) {
    final result = BroadcastTxRequest._();
    if (rawTx != null) result.rawTx = rawTx;
    if (skipTokenChecks != null) result.skipTokenChecks = skipTokenChecks;
    if (finalizationTimeoutSecs != null)
      result.finalizationTimeoutSecs = finalizationTimeoutSecs;
    return result;
  }

  BroadcastTxRequest._();

  factory BroadcastTxRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxRequest()..mergeFromBuffer(data, registry);
  factory BroadcastTxRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxRequest()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BroadcastTxRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BroadcastTxRequest.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'rawTx', $pb.PbFieldType.OY)
    ..aOB(2, _omitFieldNames ? '' : 'skipTokenChecks')
    ..a<$fixnum.Int64>(3, _omitFieldNames ? '' : 'finalizationTimeoutSecs',
        $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxRequest copyWith(void Function(BroadcastTxRequest) updates) =>
      super.copyWith((message) => updates(message as BroadcastTxRequest))
          as BroadcastTxRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use BroadcastTxRequest() / BroadcastTxRequest.new instead')
  static BroadcastTxRequest create() => BroadcastTxRequest._();
  static $pb.GeneratedMessage $_createMessage() => BroadcastTxRequest._();
  @$core.override
  BroadcastTxRequest createEmptyInstance() => BroadcastTxRequest._();
  @$core.pragma('dart2js:noInline')
  static BroadcastTxRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BroadcastTxRequest>(
          BroadcastTxRequest.$_createMessage);
  static BroadcastTxRequest? _defaultInstance;

  /// Serialized tx
  @$pb.TagNumber(1)
  $core.List<$core.int> get rawTx => $_getN(0);
  @$pb.TagNumber(1)
  set rawTx($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRawTx() => $_has(0);
  @$pb.TagNumber(1)
  void clearRawTx() => $_clearField(1);

  /// Whether to skip token checks and broadcast even if tokens are unintentionally burned
  @$pb.TagNumber(2)
  $core.bool get skipTokenChecks => $_getBF(1);
  @$pb.TagNumber(2)
  set skipTokenChecks($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSkipTokenChecks() => $_has(1);
  @$pb.TagNumber(2)
  void clearSkipTokenChecks() => $_clearField(2);

  /// Waits for finalization of the transaction before returning the request,
  /// for up to the given seconds.
  /// Set to 0 to not wait at all and return right after broadcast.
  @$pb.TagNumber(3)
  $fixnum.Int64 get finalizationTimeoutSecs => $_getI64(2);
  @$pb.TagNumber(3)
  set finalizationTimeoutSecs($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFinalizationTimeoutSecs() => $_has(2);
  @$pb.TagNumber(3)
  void clearFinalizationTimeoutSecs() => $_clearField(3);
}

/// Response of broadcasting the tx
class BroadcastTxResponse extends $pb.GeneratedMessage {
  factory BroadcastTxResponse({
    $core.List<$core.int>? txid,
  }) {
    final result = BroadcastTxResponse._();
    if (txid != null) result.txid = txid;
    return result;
  }

  BroadcastTxResponse._();

  factory BroadcastTxResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxResponse()..mergeFromBuffer(data, registry);
  factory BroadcastTxResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxResponse()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BroadcastTxResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BroadcastTxResponse.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'txid', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxResponse copyWith(void Function(BroadcastTxResponse) updates) =>
      super.copyWith((message) => updates(message as BroadcastTxResponse))
          as BroadcastTxResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core
      .Deprecated('Use BroadcastTxResponse() / BroadcastTxResponse.new instead')
  static BroadcastTxResponse create() => BroadcastTxResponse._();
  static $pb.GeneratedMessage $_createMessage() => BroadcastTxResponse._();
  @$core.override
  BroadcastTxResponse createEmptyInstance() => BroadcastTxResponse._();
  @$core.pragma('dart2js:noInline')
  static BroadcastTxResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BroadcastTxResponse>(
          BroadcastTxResponse.$_createMessage);
  static BroadcastTxResponse? _defaultInstance;

  /// TxId of the broadcast tx
  @$pb.TagNumber(1)
  $core.List<$core.int> get txid => $_getN(0);
  @$pb.TagNumber(1)
  set txid($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTxid() => $_has(0);
  @$pb.TagNumber(1)
  void clearTxid() => $_clearField(1);
}

/// Broadcast multiple txs. If one of the txs fails token validation, the entire batch will not be broadcast.
class BroadcastTxsRequest extends $pb.GeneratedMessage {
  factory BroadcastTxsRequest({
    $core.Iterable<$core.List<$core.int>>? rawTxs,
    $core.bool? skipTokenChecks,
    $fixnum.Int64? finalizationTimeoutSecs,
  }) {
    final result = BroadcastTxsRequest._();
    if (rawTxs != null) result.rawTxs.addAll(rawTxs);
    if (skipTokenChecks != null) result.skipTokenChecks = skipTokenChecks;
    if (finalizationTimeoutSecs != null)
      result.finalizationTimeoutSecs = finalizationTimeoutSecs;
    return result;
  }

  BroadcastTxsRequest._();

  factory BroadcastTxsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxsRequest()..mergeFromBuffer(data, registry);
  factory BroadcastTxsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxsRequest()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BroadcastTxsRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BroadcastTxsRequest.$_createMessage)
    ..p<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'rawTxs', $pb.PbFieldType.PY)
    ..aOB(2, _omitFieldNames ? '' : 'skipTokenChecks')
    ..a<$fixnum.Int64>(3, _omitFieldNames ? '' : 'finalizationTimeoutSecs',
        $pb.PbFieldType.OU6,
        defaultOrMaker: $fixnum.Int64.ZERO)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxsRequest copyWith(void Function(BroadcastTxsRequest) updates) =>
      super.copyWith((message) => updates(message as BroadcastTxsRequest))
          as BroadcastTxsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core
      .Deprecated('Use BroadcastTxsRequest() / BroadcastTxsRequest.new instead')
  static BroadcastTxsRequest create() => BroadcastTxsRequest._();
  static $pb.GeneratedMessage $_createMessage() => BroadcastTxsRequest._();
  @$core.override
  BroadcastTxsRequest createEmptyInstance() => BroadcastTxsRequest._();
  @$core.pragma('dart2js:noInline')
  static BroadcastTxsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BroadcastTxsRequest>(
          BroadcastTxsRequest.$_createMessage);
  static BroadcastTxsRequest? _defaultInstance;

  /// Serialized txs.
  @$pb.TagNumber(1)
  $pb.PbList<$core.List<$core.int>> get rawTxs => $_getList(0);

  /// Whether to skip token checks and broadcast even if tokens are unintentionally burned
  @$pb.TagNumber(2)
  $core.bool get skipTokenChecks => $_getBF(1);
  @$pb.TagNumber(2)
  set skipTokenChecks($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSkipTokenChecks() => $_has(1);
  @$pb.TagNumber(2)
  void clearSkipTokenChecks() => $_clearField(2);

  /// Waits for finalization of the transaction before returning the request,
  /// for up to the given seconds.
  /// Set to 0 to not wait at all and return right after broadcast.
  @$pb.TagNumber(3)
  $fixnum.Int64 get finalizationTimeoutSecs => $_getI64(2);
  @$pb.TagNumber(3)
  set finalizationTimeoutSecs($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFinalizationTimeoutSecs() => $_has(2);
  @$pb.TagNumber(3)
  void clearFinalizationTimeoutSecs() => $_clearField(3);
}

/// Response of broadcasting txs
class BroadcastTxsResponse extends $pb.GeneratedMessage {
  factory BroadcastTxsResponse({
    $core.Iterable<$core.List<$core.int>>? txids,
  }) {
    final result = BroadcastTxsResponse._();
    if (txids != null) result.txids.addAll(txids);
    return result;
  }

  BroadcastTxsResponse._();

  factory BroadcastTxsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxsResponse()..mergeFromBuffer(data, registry);
  factory BroadcastTxsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      BroadcastTxsResponse()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'BroadcastTxsResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: BroadcastTxsResponse.$_createMessage)
    ..p<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'txids', $pb.PbFieldType.PY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  BroadcastTxsResponse copyWith(void Function(BroadcastTxsResponse) updates) =>
      super.copyWith((message) => updates(message as BroadcastTxsResponse))
          as BroadcastTxsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use BroadcastTxsResponse() / BroadcastTxsResponse.new instead')
  static BroadcastTxsResponse create() => BroadcastTxsResponse._();
  static $pb.GeneratedMessage $_createMessage() => BroadcastTxsResponse._();
  @$core.override
  BroadcastTxsResponse createEmptyInstance() => BroadcastTxsResponse._();
  @$core.pragma('dart2js:noInline')
  static BroadcastTxsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<BroadcastTxsResponse>(
          BroadcastTxsResponse.$_createMessage);
  static BroadcastTxsResponse? _defaultInstance;

  /// TxIds of the broadcast txs
  @$pb.TagNumber(1)
  $pb.PbList<$core.List<$core.int>> get txids => $_getList(0);
}

/// Raw serialized tx.
class RawTx extends $pb.GeneratedMessage {
  factory RawTx({
    $core.List<$core.int>? rawTx,
  }) {
    final result = RawTx._();
    if (rawTx != null) result.rawTx = rawTx;
    return result;
  }

  RawTx._();

  factory RawTx.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      RawTx()..mergeFromBuffer(data, registry);
  factory RawTx.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      RawTx()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'RawTx',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: RawTx.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'rawTx', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RawTx clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  RawTx copyWith(void Function(RawTx) updates) =>
      super.copyWith((message) => updates(message as RawTx)) as RawTx;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use RawTx() / RawTx.new instead')
  static RawTx create() => RawTx._();
  static $pb.GeneratedMessage $_createMessage() => RawTx._();
  @$core.override
  RawTx createEmptyInstance() => RawTx._();
  @$core.pragma('dart2js:noInline')
  static RawTx getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<RawTx>(RawTx.$_createMessage);
  static RawTx? _defaultInstance;

  /// Bytes of the serialized tx.
  @$pb.TagNumber(1)
  $core.List<$core.int> get rawTx => $_getN(0);
  @$pb.TagNumber(1)
  set rawTx($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRawTx() => $_has(0);
  @$pb.TagNumber(1)
  void clearRawTx() => $_clearField(1);
}

enum WsSub_SubType {
  blocks,
  script,
  tokenId,
  lokadId,
  plugin,
  txid,
  txs,
  notSet
}

/// Subscription to WebSocket updates.
class WsSub extends $pb.GeneratedMessage {
  factory WsSub({
    $core.bool? isUnsub,
    WsSubBlocks? blocks,
    WsSubScript? script,
    WsSubTokenId? tokenId,
    WsSubLokadId? lokadId,
    WsPlugin? plugin,
    WsSubTxId? txid,
    WsSubTxs? txs,
  }) {
    final result = WsSub._();
    if (isUnsub != null) result.isUnsub = isUnsub;
    if (blocks != null) result.blocks = blocks;
    if (script != null) result.script = script;
    if (tokenId != null) result.tokenId = tokenId;
    if (lokadId != null) result.lokadId = lokadId;
    if (plugin != null) result.plugin = plugin;
    if (txid != null) result.txid = txid;
    if (txs != null) result.txs = txs;
    return result;
  }

  WsSub._();

  factory WsSub.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSub()..mergeFromBuffer(data, registry);
  factory WsSub.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSub()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, WsSub_SubType> _WsSub_SubTypeByTag = {
    2: WsSub_SubType.blocks,
    3: WsSub_SubType.script,
    4: WsSub_SubType.tokenId,
    5: WsSub_SubType.lokadId,
    6: WsSub_SubType.plugin,
    7: WsSub_SubType.txid,
    8: WsSub_SubType.txs,
    0: WsSub_SubType.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSub',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSub.$_createMessage)
    ..oo(0, [2, 3, 4, 5, 6, 7, 8])
    ..aOB(1, _omitFieldNames ? '' : 'isUnsub')
    ..aOM<WsSubBlocks>(2, _omitFieldNames ? '' : 'blocks',
        subBuilder: WsSubBlocks.$_createMessage)
    ..aOM<WsSubScript>(3, _omitFieldNames ? '' : 'script',
        subBuilder: WsSubScript.$_createMessage)
    ..aOM<WsSubTokenId>(4, _omitFieldNames ? '' : 'tokenId',
        subBuilder: WsSubTokenId.$_createMessage)
    ..aOM<WsSubLokadId>(5, _omitFieldNames ? '' : 'lokadId',
        subBuilder: WsSubLokadId.$_createMessage)
    ..aOM<WsPlugin>(6, _omitFieldNames ? '' : 'plugin',
        subBuilder: WsPlugin.$_createMessage)
    ..aOM<WsSubTxId>(7, _omitFieldNames ? '' : 'txid',
        subBuilder: WsSubTxId.$_createMessage)
    ..aOM<WsSubTxs>(8, _omitFieldNames ? '' : 'txs',
        subBuilder: WsSubTxs.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSub clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSub copyWith(void Function(WsSub) updates) =>
      super.copyWith((message) => updates(message as WsSub)) as WsSub;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSub() / WsSub.new instead')
  static WsSub create() => WsSub._();
  static $pb.GeneratedMessage $_createMessage() => WsSub._();
  @$core.override
  WsSub createEmptyInstance() => WsSub._();
  @$core.pragma('dart2js:noInline')
  static WsSub getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WsSub>(WsSub.$_createMessage);
  static WsSub? _defaultInstance;

  @$pb.TagNumber(2)
  @$pb.TagNumber(3)
  @$pb.TagNumber(4)
  @$pb.TagNumber(5)
  @$pb.TagNumber(6)
  @$pb.TagNumber(7)
  @$pb.TagNumber(8)
  WsSub_SubType whichSubType() => _WsSub_SubTypeByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(2)
  @$pb.TagNumber(3)
  @$pb.TagNumber(4)
  @$pb.TagNumber(5)
  @$pb.TagNumber(6)
  @$pb.TagNumber(7)
  @$pb.TagNumber(8)
  void clearSubType() => $_clearField($_whichOneof(0));

  /// Set this to `true` to unsubscribe from the event.
  @$pb.TagNumber(1)
  $core.bool get isUnsub => $_getBF(0);
  @$pb.TagNumber(1)
  set isUnsub($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasIsUnsub() => $_has(0);
  @$pb.TagNumber(1)
  void clearIsUnsub() => $_clearField(1);

  /// Subscription to block updates
  @$pb.TagNumber(2)
  WsSubBlocks get blocks => $_getN(1);
  @$pb.TagNumber(2)
  set blocks(WsSubBlocks value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasBlocks() => $_has(1);
  @$pb.TagNumber(2)
  void clearBlocks() => $_clearField(2);
  @$pb.TagNumber(2)
  WsSubBlocks ensureBlocks() => $_ensure(1);

  /// Subscription to a script
  @$pb.TagNumber(3)
  WsSubScript get script => $_getN(2);
  @$pb.TagNumber(3)
  set script(WsSubScript value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasScript() => $_has(2);
  @$pb.TagNumber(3)
  void clearScript() => $_clearField(3);
  @$pb.TagNumber(3)
  WsSubScript ensureScript() => $_ensure(2);

  /// Subscription to a token ID
  @$pb.TagNumber(4)
  WsSubTokenId get tokenId => $_getN(3);
  @$pb.TagNumber(4)
  set tokenId(WsSubTokenId value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasTokenId() => $_has(3);
  @$pb.TagNumber(4)
  void clearTokenId() => $_clearField(4);
  @$pb.TagNumber(4)
  WsSubTokenId ensureTokenId() => $_ensure(3);

  /// Subscription to a lokad ID
  @$pb.TagNumber(5)
  WsSubLokadId get lokadId => $_getN(4);
  @$pb.TagNumber(5)
  set lokadId(WsSubLokadId value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasLokadId() => $_has(4);
  @$pb.TagNumber(5)
  void clearLokadId() => $_clearField(5);
  @$pb.TagNumber(5)
  WsSubLokadId ensureLokadId() => $_ensure(4);

  /// Subscription to a plugin group
  @$pb.TagNumber(6)
  WsPlugin get plugin => $_getN(5);
  @$pb.TagNumber(6)
  set plugin(WsPlugin value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasPlugin() => $_has(5);
  @$pb.TagNumber(6)
  void clearPlugin() => $_clearField(6);
  @$pb.TagNumber(6)
  WsPlugin ensurePlugin() => $_ensure(5);

  /// Subscription to a txid
  @$pb.TagNumber(7)
  WsSubTxId get txid => $_getN(6);
  @$pb.TagNumber(7)
  set txid(WsSubTxId value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasTxid() => $_has(6);
  @$pb.TagNumber(7)
  void clearTxid() => $_clearField(7);
  @$pb.TagNumber(7)
  WsSubTxId ensureTxid() => $_ensure(6);

  /// Subscription to all txs
  @$pb.TagNumber(8)
  WsSubTxs get txs => $_getN(7);
  @$pb.TagNumber(8)
  set txs(WsSubTxs value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasTxs() => $_has(7);
  @$pb.TagNumber(8)
  void clearTxs() => $_clearField(8);
  @$pb.TagNumber(8)
  WsSubTxs ensureTxs() => $_ensure(7);
}

/// Subscription to blocks. They will be sent any time a block got connected,
/// disconnected or finalized.
class WsSubBlocks extends $pb.GeneratedMessage {
  factory WsSubBlocks() => WsSubBlocks._();

  WsSubBlocks._();

  factory WsSubBlocks.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubBlocks()..mergeFromBuffer(data, registry);
  factory WsSubBlocks.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubBlocks()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubBlocks',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubBlocks.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubBlocks clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubBlocks copyWith(void Function(WsSubBlocks) updates) =>
      super.copyWith((message) => updates(message as WsSubBlocks))
          as WsSubBlocks;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubBlocks() / WsSubBlocks.new instead')
  static WsSubBlocks create() => WsSubBlocks._();
  static $pb.GeneratedMessage $_createMessage() => WsSubBlocks._();
  @$core.override
  WsSubBlocks createEmptyInstance() => WsSubBlocks._();
  @$core.pragma('dart2js:noInline')
  static WsSubBlocks getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WsSubBlocks>(
          WsSubBlocks.$_createMessage);
  static WsSubBlocks? _defaultInstance;
}

/// Subscription to all txs.
class WsSubTxs extends $pb.GeneratedMessage {
  factory WsSubTxs() => WsSubTxs._();

  WsSubTxs._();

  factory WsSubTxs.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTxs()..mergeFromBuffer(data, registry);
  factory WsSubTxs.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTxs()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubTxs',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubTxs.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTxs clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTxs copyWith(void Function(WsSubTxs) updates) =>
      super.copyWith((message) => updates(message as WsSubTxs)) as WsSubTxs;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubTxs() / WsSubTxs.new instead')
  static WsSubTxs create() => WsSubTxs._();
  static $pb.GeneratedMessage $_createMessage() => WsSubTxs._();
  @$core.override
  WsSubTxs createEmptyInstance() => WsSubTxs._();
  @$core.pragma('dart2js:noInline')
  static WsSubTxs getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WsSubTxs>(WsSubTxs.$_createMessage);
  static WsSubTxs? _defaultInstance;
}

/// Subscription to a script. They will be sent every time a tx spending the
/// given script or sending to the given script has been added to/removed from
/// the mempool, or confirmed in a block.
class WsSubScript extends $pb.GeneratedMessage {
  factory WsSubScript({
    $core.String? scriptType,
    $core.List<$core.int>? payload,
  }) {
    final result = WsSubScript._();
    if (scriptType != null) result.scriptType = scriptType;
    if (payload != null) result.payload = payload;
    return result;
  }

  WsSubScript._();

  factory WsSubScript.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubScript()..mergeFromBuffer(data, registry);
  factory WsSubScript.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubScript()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubScript',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubScript.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'scriptType')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'payload', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubScript clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubScript copyWith(void Function(WsSubScript) updates) =>
      super.copyWith((message) => updates(message as WsSubScript))
          as WsSubScript;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubScript() / WsSubScript.new instead')
  static WsSubScript create() => WsSubScript._();
  static $pb.GeneratedMessage $_createMessage() => WsSubScript._();
  @$core.override
  WsSubScript createEmptyInstance() => WsSubScript._();
  @$core.pragma('dart2js:noInline')
  static WsSubScript getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WsSubScript>(
          WsSubScript.$_createMessage);
  static WsSubScript? _defaultInstance;

  /// Script type to subscribe to ("p2pkh", "p2sh", "p2pk", "other").
  @$pb.TagNumber(1)
  $core.String get scriptType => $_getSZ(0);
  @$pb.TagNumber(1)
  set scriptType($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasScriptType() => $_has(0);
  @$pb.TagNumber(1)
  void clearScriptType() => $_clearField(1);

  /// Payload for the given script type:
  /// - 20-byte hash for "p2pkh" and "p2sh"
  /// - 33-byte or 65-byte pubkey for "p2pk"
  /// - Serialized script for "other"
  @$pb.TagNumber(2)
  $core.List<$core.int> get payload => $_getN(1);
  @$pb.TagNumber(2)
  set payload($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPayload() => $_has(1);
  @$pb.TagNumber(2)
  void clearPayload() => $_clearField(2);
}

/// Subscription to a token ID. They will be sent every time a tx spending or
/// sending tokens with the token ID.
class WsSubTokenId extends $pb.GeneratedMessage {
  factory WsSubTokenId({
    $core.String? tokenId,
  }) {
    final result = WsSubTokenId._();
    if (tokenId != null) result.tokenId = tokenId;
    return result;
  }

  WsSubTokenId._();

  factory WsSubTokenId.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTokenId()..mergeFromBuffer(data, registry);
  factory WsSubTokenId.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTokenId()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubTokenId',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubTokenId.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'tokenId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTokenId clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTokenId copyWith(void Function(WsSubTokenId) updates) =>
      super.copyWith((message) => updates(message as WsSubTokenId))
          as WsSubTokenId;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubTokenId() / WsSubTokenId.new instead')
  static WsSubTokenId create() => WsSubTokenId._();
  static $pb.GeneratedMessage $_createMessage() => WsSubTokenId._();
  @$core.override
  WsSubTokenId createEmptyInstance() => WsSubTokenId._();
  @$core.pragma('dart2js:noInline')
  static WsSubTokenId getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WsSubTokenId>(
          WsSubTokenId.$_createMessage);
  static WsSubTokenId? _defaultInstance;

  /// Hex token ID to subscribe to.
  @$pb.TagNumber(1)
  $core.String get tokenId => $_getSZ(0);
  @$pb.TagNumber(1)
  set tokenId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTokenId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTokenId() => $_clearField(1);
}

/// Subscription to a LOKAD ID. They will be sent every time a tx matches the given LOKAD ID in one of the following ways:
/// - `OP_RETURN <LOKAD ID> ...`: The first output has an OP_RETURN with the given LOKAD ID as first pushop
/// - `OP_RETURN OP_RESERVED "<LOKAD_ID>..." "<LOKAD_ID>..." ...`: The first output has an eMPP encoded OP_RETURN, and one (or more) of the pushops has the LOKAD ID as prefix.
/// - `<LOKAD ID> ...`: An input's scriptSig has the given LOKAD ID as the first pushop
class WsSubLokadId extends $pb.GeneratedMessage {
  factory WsSubLokadId({
    $core.List<$core.int>? lokadId,
  }) {
    final result = WsSubLokadId._();
    if (lokadId != null) result.lokadId = lokadId;
    return result;
  }

  WsSubLokadId._();

  factory WsSubLokadId.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubLokadId()..mergeFromBuffer(data, registry);
  factory WsSubLokadId.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubLokadId()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubLokadId',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubLokadId.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'lokadId', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubLokadId clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubLokadId copyWith(void Function(WsSubLokadId) updates) =>
      super.copyWith((message) => updates(message as WsSubLokadId))
          as WsSubLokadId;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubLokadId() / WsSubLokadId.new instead')
  static WsSubLokadId create() => WsSubLokadId._();
  static $pb.GeneratedMessage $_createMessage() => WsSubLokadId._();
  @$core.override
  WsSubLokadId createEmptyInstance() => WsSubLokadId._();
  @$core.pragma('dart2js:noInline')
  static WsSubLokadId getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WsSubLokadId>(
          WsSubLokadId.$_createMessage);
  static WsSubLokadId? _defaultInstance;

  /// 4-byte LOKAD ID.
  @$pb.TagNumber(1)
  $core.List<$core.int> get lokadId => $_getN(0);
  @$pb.TagNumber(1)
  set lokadId($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasLokadId() => $_has(0);
  @$pb.TagNumber(1)
  void clearLokadId() => $_clearField(1);
}

/// Subscription to a group assigned by a plugin to outputs.
class WsPlugin extends $pb.GeneratedMessage {
  factory WsPlugin({
    $core.String? pluginName,
    $core.List<$core.int>? group,
  }) {
    final result = WsPlugin._();
    if (pluginName != null) result.pluginName = pluginName;
    if (group != null) result.group = group;
    return result;
  }

  WsPlugin._();

  factory WsPlugin.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsPlugin()..mergeFromBuffer(data, registry);
  factory WsPlugin.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsPlugin()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsPlugin',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsPlugin.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'pluginName')
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'group', $pb.PbFieldType.OY)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsPlugin clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsPlugin copyWith(void Function(WsPlugin) updates) =>
      super.copyWith((message) => updates(message as WsPlugin)) as WsPlugin;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsPlugin() / WsPlugin.new instead')
  static WsPlugin create() => WsPlugin._();
  static $pb.GeneratedMessage $_createMessage() => WsPlugin._();
  @$core.override
  WsPlugin createEmptyInstance() => WsPlugin._();
  @$core.pragma('dart2js:noInline')
  static WsPlugin getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WsPlugin>(WsPlugin.$_createMessage);
  static WsPlugin? _defaultInstance;

  /// Name of the plugin to subscribe to
  @$pb.TagNumber(1)
  $core.String get pluginName => $_getSZ(0);
  @$pb.TagNumber(1)
  set pluginName($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPluginName() => $_has(0);
  @$pb.TagNumber(1)
  void clearPluginName() => $_clearField(1);

  /// Group assigned by the plugin to subscribe to
  @$pb.TagNumber(2)
  $core.List<$core.int> get group => $_getN(1);
  @$pb.TagNumber(2)
  set group($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasGroup() => $_has(1);
  @$pb.TagNumber(2)
  void clearGroup() => $_clearField(2);
}

/// Subscription to a txid. They will be sent every time a tx status confirmation changes.
class WsSubTxId extends $pb.GeneratedMessage {
  factory WsSubTxId({
    $core.String? txid,
  }) {
    final result = WsSubTxId._();
    if (txid != null) result.txid = txid;
    return result;
  }

  WsSubTxId._();

  factory WsSubTxId.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTxId()..mergeFromBuffer(data, registry);
  factory WsSubTxId.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsSubTxId()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsSubTxId',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsSubTxId.$_createMessage)
    ..aOS(1, _omitFieldNames ? '' : 'txid')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTxId clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsSubTxId copyWith(void Function(WsSubTxId) updates) =>
      super.copyWith((message) => updates(message as WsSubTxId)) as WsSubTxId;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsSubTxId() / WsSubTxId.new instead')
  static WsSubTxId create() => WsSubTxId._();
  static $pb.GeneratedMessage $_createMessage() => WsSubTxId._();
  @$core.override
  WsSubTxId createEmptyInstance() => WsSubTxId._();
  @$core.pragma('dart2js:noInline')
  static WsSubTxId getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WsSubTxId>(WsSubTxId.$_createMessage);
  static WsSubTxId? _defaultInstance;

  /// Hex txid to subscribe to.
  @$pb.TagNumber(1)
  $core.String get txid => $_getSZ(0);
  @$pb.TagNumber(1)
  set txid($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTxid() => $_has(0);
  @$pb.TagNumber(1)
  void clearTxid() => $_clearField(1);
}

enum WsMsg_MsgType { error, block, tx, notSet }

/// Message coming from the WebSocket
class WsMsg extends $pb.GeneratedMessage {
  factory WsMsg({
    Error? error,
    MsgBlock? block,
    MsgTx? tx,
  }) {
    final result = WsMsg._();
    if (error != null) result.error = error;
    if (block != null) result.block = block;
    if (tx != null) result.tx = tx;
    return result;
  }

  WsMsg._();

  factory WsMsg.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsMsg()..mergeFromBuffer(data, registry);
  factory WsMsg.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      WsMsg()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, WsMsg_MsgType> _WsMsg_MsgTypeByTag = {
    1: WsMsg_MsgType.error,
    2: WsMsg_MsgType.block,
    3: WsMsg_MsgType.tx,
    0: WsMsg_MsgType.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WsMsg',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: WsMsg.$_createMessage)
    ..oo(0, [1, 2, 3])
    ..aOM<Error>(1, _omitFieldNames ? '' : 'error',
        subBuilder: Error.$_createMessage)
    ..aOM<MsgBlock>(2, _omitFieldNames ? '' : 'block',
        subBuilder: MsgBlock.$_createMessage)
    ..aOM<MsgTx>(3, _omitFieldNames ? '' : 'tx',
        subBuilder: MsgTx.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsMsg clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WsMsg copyWith(void Function(WsMsg) updates) =>
      super.copyWith((message) => updates(message as WsMsg)) as WsMsg;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use WsMsg() / WsMsg.new instead')
  static WsMsg create() => WsMsg._();
  static $pb.GeneratedMessage $_createMessage() => WsMsg._();
  @$core.override
  WsMsg createEmptyInstance() => WsMsg._();
  @$core.pragma('dart2js:noInline')
  static WsMsg getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WsMsg>(WsMsg.$_createMessage);
  static WsMsg? _defaultInstance;

  @$pb.TagNumber(1)
  @$pb.TagNumber(2)
  @$pb.TagNumber(3)
  WsMsg_MsgType whichMsgType() => _WsMsg_MsgTypeByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(1)
  @$pb.TagNumber(2)
  @$pb.TagNumber(3)
  void clearMsgType() => $_clearField($_whichOneof(0));

  /// Error, e.g. when a bad message has been sent into the WebSocket.
  @$pb.TagNumber(1)
  Error get error => $_getN(0);
  @$pb.TagNumber(1)
  set error(Error value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasError() => $_has(0);
  @$pb.TagNumber(1)
  void clearError() => $_clearField(1);
  @$pb.TagNumber(1)
  Error ensureError() => $_ensure(0);

  /// Block got connected, disconnected, finalized, etc.
  @$pb.TagNumber(2)
  MsgBlock get block => $_getN(1);
  @$pb.TagNumber(2)
  set block(MsgBlock value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasBlock() => $_has(1);
  @$pb.TagNumber(2)
  void clearBlock() => $_clearField(2);
  @$pb.TagNumber(2)
  MsgBlock ensureBlock() => $_ensure(1);

  /// Tx got added to/removed from the mempool, or confirmed in a block.
  @$pb.TagNumber(3)
  MsgTx get tx => $_getN(2);
  @$pb.TagNumber(3)
  set tx(MsgTx value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasTx() => $_has(2);
  @$pb.TagNumber(3)
  void clearTx() => $_clearField(3);
  @$pb.TagNumber(3)
  MsgTx ensureTx() => $_ensure(2);
}

/// The relevant coinbase data
class CoinbaseData extends $pb.GeneratedMessage {
  factory CoinbaseData({
    $core.List<$core.int>? coinbaseScriptsig,
    $core.Iterable<TxOutput>? coinbaseOutputs,
  }) {
    final result = CoinbaseData._();
    if (coinbaseScriptsig != null) result.coinbaseScriptsig = coinbaseScriptsig;
    if (coinbaseOutputs != null) result.coinbaseOutputs.addAll(coinbaseOutputs);
    return result;
  }

  CoinbaseData._();

  factory CoinbaseData.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      CoinbaseData()..mergeFromBuffer(data, registry);
  factory CoinbaseData.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      CoinbaseData()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CoinbaseData',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: CoinbaseData.$_createMessage)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'coinbaseScriptsig', $pb.PbFieldType.OY)
    ..pPM<TxOutput>(2, _omitFieldNames ? '' : 'coinbaseOutputs',
        subBuilder: TxOutput.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CoinbaseData clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CoinbaseData copyWith(void Function(CoinbaseData) updates) =>
      super.copyWith((message) => updates(message as CoinbaseData))
          as CoinbaseData;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use CoinbaseData() / CoinbaseData.new instead')
  static CoinbaseData create() => CoinbaseData._();
  static $pb.GeneratedMessage $_createMessage() => CoinbaseData._();
  @$core.override
  CoinbaseData createEmptyInstance() => CoinbaseData._();
  @$core.pragma('dart2js:noInline')
  static CoinbaseData getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CoinbaseData>(
          CoinbaseData.$_createMessage);
  static CoinbaseData? _defaultInstance;

  /// The coinbase input scriptsig
  @$pb.TagNumber(1)
  $core.List<$core.int> get coinbaseScriptsig => $_getN(0);
  @$pb.TagNumber(1)
  set coinbaseScriptsig($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasCoinbaseScriptsig() => $_has(0);
  @$pb.TagNumber(1)
  void clearCoinbaseScriptsig() => $_clearField(1);

  /// Outputs of the coinbase tx
  @$pb.TagNumber(2)
  $pb.PbList<TxOutput> get coinbaseOutputs => $_getList(1);
}

/// Block got connected, disconnected, finalized, invalidated, etc.
class MsgBlock extends $pb.GeneratedMessage {
  factory MsgBlock({
    BlockMsgType? msgType,
    $core.List<$core.int>? blockHash,
    $core.int? blockHeight,
    $fixnum.Int64? blockTimestamp,
    CoinbaseData? coinbaseData,
  }) {
    final result = MsgBlock._();
    if (msgType != null) result.msgType = msgType;
    if (blockHash != null) result.blockHash = blockHash;
    if (blockHeight != null) result.blockHeight = blockHeight;
    if (blockTimestamp != null) result.blockTimestamp = blockTimestamp;
    if (coinbaseData != null) result.coinbaseData = coinbaseData;
    return result;
  }

  MsgBlock._();

  factory MsgBlock.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      MsgBlock()..mergeFromBuffer(data, registry);
  factory MsgBlock.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      MsgBlock()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MsgBlock',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: MsgBlock.$_createMessage)
    ..aE<BlockMsgType>(1, _omitFieldNames ? '' : 'msgType',
        enumValues: BlockMsgType.values)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'blockHash', $pb.PbFieldType.OY)
    ..aI(3, _omitFieldNames ? '' : 'blockHeight')
    ..aInt64(4, _omitFieldNames ? '' : 'blockTimestamp')
    ..aOM<CoinbaseData>(5, _omitFieldNames ? '' : 'coinbaseData',
        subBuilder: CoinbaseData.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MsgBlock clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MsgBlock copyWith(void Function(MsgBlock) updates) =>
      super.copyWith((message) => updates(message as MsgBlock)) as MsgBlock;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use MsgBlock() / MsgBlock.new instead')
  static MsgBlock create() => MsgBlock._();
  static $pb.GeneratedMessage $_createMessage() => MsgBlock._();
  @$core.override
  MsgBlock createEmptyInstance() => MsgBlock._();
  @$core.pragma('dart2js:noInline')
  static MsgBlock getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MsgBlock>(MsgBlock.$_createMessage);
  static MsgBlock? _defaultInstance;

  /// What happened to the block
  @$pb.TagNumber(1)
  BlockMsgType get msgType => $_getN(0);
  @$pb.TagNumber(1)
  set msgType(BlockMsgType value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasMsgType() => $_has(0);
  @$pb.TagNumber(1)
  void clearMsgType() => $_clearField(1);

  /// Hash of the block (little-endian)
  @$pb.TagNumber(2)
  $core.List<$core.int> get blockHash => $_getN(1);
  @$pb.TagNumber(2)
  set blockHash($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasBlockHash() => $_has(1);
  @$pb.TagNumber(2)
  void clearBlockHash() => $_clearField(2);

  /// Height of the block
  @$pb.TagNumber(3)
  $core.int get blockHeight => $_getIZ(2);
  @$pb.TagNumber(3)
  set blockHeight($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasBlockHeight() => $_has(2);
  @$pb.TagNumber(3)
  void clearBlockHeight() => $_clearField(3);

  /// Timestamp field of the block
  @$pb.TagNumber(4)
  $fixnum.Int64 get blockTimestamp => $_getI64(3);
  @$pb.TagNumber(4)
  set blockTimestamp($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasBlockTimestamp() => $_has(3);
  @$pb.TagNumber(4)
  void clearBlockTimestamp() => $_clearField(4);

  /// The coinbase data, only available if the block is disconnected or
  /// invalidated
  @$pb.TagNumber(5)
  CoinbaseData get coinbaseData => $_getN(4);
  @$pb.TagNumber(5)
  set coinbaseData(CoinbaseData value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasCoinbaseData() => $_has(4);
  @$pb.TagNumber(5)
  void clearCoinbaseData() => $_clearField(5);
  @$pb.TagNumber(5)
  CoinbaseData ensureCoinbaseData() => $_ensure(4);
}

/// The reason that caused a tx to finalize
class TxFinalizationReason extends $pb.GeneratedMessage {
  factory TxFinalizationReason({
    TxFinalizationReasonType? finalizationType,
  }) {
    final result = TxFinalizationReason._();
    if (finalizationType != null) result.finalizationType = finalizationType;
    return result;
  }

  TxFinalizationReason._();

  factory TxFinalizationReason.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxFinalizationReason()..mergeFromBuffer(data, registry);
  factory TxFinalizationReason.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      TxFinalizationReason()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TxFinalizationReason',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: TxFinalizationReason.$_createMessage)
    ..aE<TxFinalizationReasonType>(1, _omitFieldNames ? '' : 'finalizationType',
        enumValues: TxFinalizationReasonType.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxFinalizationReason clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TxFinalizationReason copyWith(void Function(TxFinalizationReason) updates) =>
      super.copyWith((message) => updates(message as TxFinalizationReason))
          as TxFinalizationReason;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated(
      'Use TxFinalizationReason() / TxFinalizationReason.new instead')
  static TxFinalizationReason create() => TxFinalizationReason._();
  static $pb.GeneratedMessage $_createMessage() => TxFinalizationReason._();
  @$core.override
  TxFinalizationReason createEmptyInstance() => TxFinalizationReason._();
  @$core.pragma('dart2js:noInline')
  static TxFinalizationReason getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TxFinalizationReason>(
          TxFinalizationReason.$_createMessage);
  static TxFinalizationReason? _defaultInstance;

  /// What kind of finalization occured
  @$pb.TagNumber(1)
  TxFinalizationReasonType get finalizationType => $_getN(0);
  @$pb.TagNumber(1)
  set finalizationType(TxFinalizationReasonType value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasFinalizationType() => $_has(0);
  @$pb.TagNumber(1)
  void clearFinalizationType() => $_clearField(1);
}

/// Tx got added to/removed from mempool, or confirmed in a block, etc.
class MsgTx extends $pb.GeneratedMessage {
  factory MsgTx({
    TxMsgType? msgType,
    $core.List<$core.int>? txid,
    TxFinalizationReason? finalizationReason,
  }) {
    final result = MsgTx._();
    if (msgType != null) result.msgType = msgType;
    if (txid != null) result.txid = txid;
    if (finalizationReason != null)
      result.finalizationReason = finalizationReason;
    return result;
  }

  MsgTx._();

  factory MsgTx.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      MsgTx()..mergeFromBuffer(data, registry);
  factory MsgTx.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      MsgTx()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MsgTx',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: MsgTx.$_createMessage)
    ..aE<TxMsgType>(1, _omitFieldNames ? '' : 'msgType',
        enumValues: TxMsgType.values)
    ..a<$core.List<$core.int>>(
        2, _omitFieldNames ? '' : 'txid', $pb.PbFieldType.OY)
    ..aOM<TxFinalizationReason>(3, _omitFieldNames ? '' : 'finalizationReason',
        subBuilder: TxFinalizationReason.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MsgTx clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MsgTx copyWith(void Function(MsgTx) updates) =>
      super.copyWith((message) => updates(message as MsgTx)) as MsgTx;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use MsgTx() / MsgTx.new instead')
  static MsgTx create() => MsgTx._();
  static $pb.GeneratedMessage $_createMessage() => MsgTx._();
  @$core.override
  MsgTx createEmptyInstance() => MsgTx._();
  @$core.pragma('dart2js:noInline')
  static MsgTx getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MsgTx>(MsgTx.$_createMessage);
  static MsgTx? _defaultInstance;

  /// What happened to the tx
  @$pb.TagNumber(1)
  TxMsgType get msgType => $_getN(0);
  @$pb.TagNumber(1)
  set msgType(TxMsgType value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasMsgType() => $_has(0);
  @$pb.TagNumber(1)
  void clearMsgType() => $_clearField(1);

  /// Txid of the tx (little-endian)
  @$pb.TagNumber(2)
  $core.List<$core.int> get txid => $_getN(1);
  @$pb.TagNumber(2)
  set txid($core.List<$core.int> value) => $_setBytes(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTxid() => $_has(1);
  @$pb.TagNumber(2)
  void clearTxid() => $_clearField(2);

  /// If the transaction is finalized, whether it's from pre-consensus or
  /// post-consensus
  @$pb.TagNumber(3)
  TxFinalizationReason get finalizationReason => $_getN(2);
  @$pb.TagNumber(3)
  set finalizationReason(TxFinalizationReason value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasFinalizationReason() => $_has(2);
  @$pb.TagNumber(3)
  void clearFinalizationReason() => $_clearField(3);
  @$pb.TagNumber(3)
  TxFinalizationReason ensureFinalizationReason() => $_ensure(2);
}

/// Empty msg without any data
class Empty extends $pb.GeneratedMessage {
  factory Empty() => Empty._();

  Empty._();

  factory Empty.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Empty()..mergeFromBuffer(data, registry);
  factory Empty.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Empty()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Empty',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Empty.$_createMessage)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Empty clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Empty copyWith(void Function(Empty) updates) =>
      super.copyWith((message) => updates(message as Empty)) as Empty;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Empty() / Empty.new instead')
  static Empty create() => Empty._();
  static $pb.GeneratedMessage $_createMessage() => Empty._();
  @$core.override
  Empty createEmptyInstance() => Empty._();
  @$core.pragma('dart2js:noInline')
  static Empty getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Empty>(Empty.$_createMessage);
  static Empty? _defaultInstance;
}

/// Error message returned from our APIs.
class Error extends $pb.GeneratedMessage {
  factory Error({
    $core.String? msg,
  }) {
    final result = Error._();
    if (msg != null) result.msg = msg;
    return result;
  }

  Error._();

  factory Error.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Error()..mergeFromBuffer(data, registry);
  factory Error.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      Error()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Error',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'chronik'),
      createEmptyInstance: Error.$_createMessage)
    ..aOS(2, _omitFieldNames ? '' : 'msg')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Error clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Error copyWith(void Function(Error) updates) =>
      super.copyWith((message) => updates(message as Error)) as Error;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  @$core.Deprecated('Use Error() / Error.new instead')
  static Error create() => Error._();
  static $pb.GeneratedMessage $_createMessage() => Error._();
  @$core.override
  Error createEmptyInstance() => Error._();
  @$core.pragma('dart2js:noInline')
  static Error getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<Error>(Error.$_createMessage);
  static Error? _defaultInstance;

  /// 2, as legacy chronik uses this for the message so we're still compatible.
  @$pb.TagNumber(2)
  $core.String get msg => $_getSZ(0);
  @$pb.TagNumber(2)
  set msg($core.String value) => $_setString(0, value);
  @$pb.TagNumber(2)
  $core.bool hasMsg() => $_has(0);
  @$pb.TagNumber(2)
  void clearMsg() => $_clearField(2);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
