# Txid endianness helper

Explorers usually display a txid in **big-endian hex**.

Bitcoin’s legacy wire format stores tx hashes inside inputs as **little-endian** bytes.

This repo includes helpers:

```bash
btc-pure txid to-wire   <explorer_txid_hex>   # big-endian -> little-endian
btc-pure txid from-wire <wire_txid_le_hex>    # little-endian -> big-endian
```

