"""Lotus naming for proposed C++ identifiers; preserve real historical references."""
import re
from pathlib import Path
EXPLICIT={
'on_tx_admitted':'OnTransactionAdmitted','on_tx_removed':'OnTransactionRemoved','on_tx_body_removed':'OnTransactionBodyRemoved','on_tx_bodies_result':'OnTransactionBodiesResult','on_message':'OnMessage','on_timer':'OnTimer','on_peer_connected':'OnPeerConnected','on_peer_disconnected':'OnPeerDisconnected','on_new_tip':'OnNewTip','on_block_disconnected':'OnBlockDisconnected',
'schedule_includes':'ScheduleIncludes','in_reference':'inReference','max_set_size':'maximumSetSize','max_symbols_per_reply':'maximumSymbolsPerReply','max_symbol_index':'maximumSymbolIndex','max_exclusions':'maximumExclusions','beta_max':'maximumAdversaryFraction','rng_seed':'randomSeed','protocol_version':'protocolVersion','short_id':'shortID','tx_hash':'transactionHash','expected_tx_hash':'expectedTransactionHash','fetch_id':'fetchID','poll_id':'pollID','last_api_error':'lastAPIError','tip_context':'tipContext',
'TxHandle':'TransactionHandle','TxHash':'TransactionHash','TxId':'TransactionID','ShortId':'ShortID','PeerId':'PeerID','TipParams':'TipParameters','PeerCaps':'PeerCapabilities','txids':'transactionIDs','txid':'transactionID','Config':'Configuration','Stats':'NodeStatistics','RootFn':'RootFunction',
'D_max':'MAXIMUM_PEERS','d_max':'MAXIMUM_TABLE_DIFFERENCE','R_ID':'admittedIDs','Delta_hat_now_i':'estimatedCurrentDifferenceAtSample','Delta_hat_now':'estimatedCurrentDifference','Delta_hat_start':'estimatedRoundStartDifference','Delta_hat':'estimatedDifference','Delta_probe':'estimatedProbeDifference','W_before':'previousCandidates','W_j':'peerCandidates','n_x':'voteCount','yes_x':'yesVoteCount','no_x':'noVoteCount','y_s':'sideVoteCount','t_maj':'majorityAnswerTime','P_hat':'EstimatedDecodeProbability','F_d':'DifferenceCDF','H_reply':'REPLY_HEADER_BYTES','H_poll':'POLL_HEADER_BYTES','H_diff':'DIFFERENCE_HEADER_BYTES','cached_n':'cachedSymbolCount','exclusions_j':'peerExclusions','sum_empty':'emptyCellSum','sum_nonempty':'nonemptyCellSum','mean_i':'sampleMean','p_i':'inclusionProbability',
'B_root':'ROOT_ERROR_TARGET','B_tx':'TRANSACTION_ERROR_TARGET','beta_c':'consecutiveSuccessThreshold',
}
EXTERNAL={'invalid_argument','static_assert'}
def Camel(token):
    parts=token.split('_')
    return parts[0]+''.join(p[:1].upper()+p[1:] for p in parts[1:])
def Apply(text,is_tests=False):
    protected={}
    def protect(match):
        token=f'ZZPROTECTEDTOKEN{len(protected)}ZZ';protected[token]=match.group();return token
    if is_tests:
        a=text.index('## Existing frozen cases');b=text.index('## Other retained case obligations')
        original=text[a:b];key='ZZHISTORICALINVENTORYZZ';protected[key]=original;text=text[:a]+key+text[b:]
    # Existing paths and standard library spellings are documentary references.
    text=re.sub(r'(?:[.~]?[A-Za-z0-9_{}.,-]+/)*[A-Za-z0-9_{}.,-]+\.(?:cpp|h|py|csv|md|txt|json|sha256|cmake)\b',protect,text)
    mapping=dict(EXPLICIT)
    for token in set(re.findall(r'\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b',text)):
        if token in mapping or token in EXTERNAL or token.isupper():continue
        if re.match(r'T\d+_',token):mapping[token]=''.join(p[:1].upper()+p[1:] for p in token.split('_'))
        else:mapping[token]=Camel(token)
    for token in sorted(mapping,key=len,reverse=True):text=re.sub(r'\b'+re.escape(token)+r'\b',mapping[token],text)
    # Standalone primitive routines are functions, not lowerCamelCase variables.
    for old,new in [('inv','Invert'),('solve','Solve'),('decode','Decode'),('encode','Encode'),('S','RequiredSymbols')]:text=re.sub(r'\b'+old+r'(?=\()',new,text)
    text=text.replace('DifferenceCDF(n)', 'DifferenceCDF(d,n)')
    text=text.replace('F_{estimatedCurrentDifferenceAtSample}(n)', 'DifferenceCDF(estimatedCurrentDifferenceAtSample,n)')
    text=text.replace('NodeStatistics stats() const','NodeStatistics GetStatistics() const').replace('stats()','GetStatistics()')
    text=text.replace('Configuration cfg','Configuration configuration')
    for key,value in protected.items():text=text.replace(key,value)
    return text,mapping
