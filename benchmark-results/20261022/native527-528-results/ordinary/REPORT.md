# Corrected527 vs528: ordinary RPC500k, four rotated pairs

All8casesPASS; each500000timed+800warmup originaccepts andall3exact500800uniqueTxIdsets/digests. Fullgates1187/1200 passed beforetiming; bothmatchedjemallocOFF/walletOFF/ChronikOFF/Release-O3assertions. Eightpersistentwriters, JSONarrays50 independent sendrawtransaction calls. No sampler. Setup/funding/signing excluded, observer250msincludedruntimeoverhead. Onehostwhitelistedhighbandwidth/fullscope1/noAVA; notWAN/defaultnetwork/maxTPS/confirmedblocks/AVAfinalization. Freshfixturebytesdiffer, native207B/fee10000shape/unique500kcount matches.

| Pair/order |527 origin s |528 origin s |527 allpeer s |528 allpeer s |
|---|---:|---:|---:|---:|
|1 / 527→528|22.255926|22.114418|23.380170|22.371775|
|2 / 528→527|22.733612|23.093582|22.902650|23.389235|
|3 / 527→528|22.987536|22.883246|23.890507|23.140740|
|4 / 528→527|22.252343|22.158841|22.360254|22.369571|

Medianobservedacceptance527 **22229.9/s** vs528 **22207.2/s**: practicalparity, no consistentordinaryRPCspeedup. Medianallpeerpollcompletion 23.141 vs22.756s; pollingupperbounds/variation, notacertifiednetworkgain. Nostatisticalconfidence/maxclaimfromfourpairs.

527: source`0f42fcfde6d36fd4326b8de18df17ce740b22446` tree`a2c855dc0f6d16fa260549c40958ba37aecb03b9` binary`7ca9d8a37f849ce5c2dadb76914cc7c7aeba4dc5bf12c695847d4d83766caa5c`. WholecasePGpeakGiBrange`[5.8753662109375, 6.878814697265625]`; includesfunding/client/peers, notliveallocation/leakproof.

528: source`922eb4a7f9d8ec8af7a5e64d521454c572ece937` tree`1c267e0b5b115f216d5d88731074f4ac794f7a4f` binary`3dc28247e6ebffb110da554476cbb592bdcfef420225de82ba74bd04feb667f8`. WholecasePGpeakGiBrange`[6.29345703125, 7.1658935546875]`; includesfunding/client/peers, notliveallocation/leakproof.

Allownedgroupsabsent; ordinarymatrixsession26157exit0. Parentnotified. Loadedreads/dedicatedbatch/recovery areseparatecases, notinferredfromthisordinaryresult. InputENDPOINTS,toolhashes,percaseplans/adaptedworkload/provenance/resource/progress/fixturehashes preservedalongside. No timingfrompriorredgatesincluded.
