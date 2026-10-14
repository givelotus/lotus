use sha2::Digest;

pub fn lotus_hash(header: &[u8; 160]) -> [u8; 32] {
    let tx_layer_hash = sha2::Sha256::digest(&header[52..]);
    let mut pow_layer = [0u8; 52];
    pow_layer[..20].copy_from_slice(&header[32..52]);
    pow_layer[20..].copy_from_slice(&tx_layer_hash[..]);
    let pow_layer_hash = sha2::Sha256::digest(&pow_layer);
    let mut chain_layer = [0u8; 64];
    chain_layer[..32].copy_from_slice(&header[..32]);
    chain_layer[32..].copy_from_slice(&pow_layer_hash);
    sha2::Sha256::digest(&chain_layer).into()
}

#[test]
fn test_lotus_hash() {
    use hex_literal::hex;
    let header = hex!("0000000000000000000000000000000000000000000000000000000000000000ffff001d00c273600000000041c6ddd303000000010e010000000000000000000000000000000000000000000000000000000000000000000000000000000000934755d60e905ec8778f554164bd9b7f21ab6c15cfed2956123a722a6f6fa62e1406e05881e299367766d313e26c05564ec91bf721d31726bd6e46e60689539a");
    let mut hash = lotus_hash(&header);
    hash.reverse();
    assert_eq!(
        hex::encode(hash),
        "000000006275dc5039da85620773f3223d629759495f80b49a381d79cae77c11"
    );
}

#[test]
fn test_mainnet_genesis_hash() {
    // Mainnet header returned by lotus-cli getblockheader at height zero.
    let header = hex_literal::hex!("00000000000000000000000000000000000000000000000000000000000000000000101cf407d06000000000ab78287d559f2c63017b0100000000000000000000000000000000000000000000000000000000000000000000000000000000004cf30ab9dc2797f3a4fe5f6b2dbf11670bf97e5aa266d3a6adcd708fd892f3371406e05881e299367766d313e26c05564ec91bf721d31726bd6e46e60689539a");
    let mut hash = lotus_hash(&header);
    hash.reverse();
    assert_eq!(
        hex::encode(hash),
        "000000000abc0cde58ee7e919d3d4de183e6844add1fd5d14b4eac89d958f470"
    );
}
