#!/bin/bash
cd "$(dirname "$0")"
echo "adv seed share" > sweep10.txt
for adv in 0 32 64 128 256 512; do
  for seed in $(seq 1 10); do
    d=w-$adv-$seed
    python3 gen_exp.py $adv $d $seed > /dev/null
    ( cd $d && rm -rf shadow.data && timeout 900 env PATH=$HOME/.local/bin:/usr/sbin:$PATH shadow --template-directory shadow.data.template shadow.yaml > shadow.log 2>&1 )
    python3 -c "
import sys, io, contextlib; sys.argv=['x','$d']; sys.path.insert(0,'.')
import analyze
buf=io.StringIO()
with contextlib.redirect_stdout(buf): s=analyze.main()
print(f'$adv $seed {s:.4f}')" >> sweep10.txt
    rm -rf $d
  done
done
echo DONE >> sweep10.txt
