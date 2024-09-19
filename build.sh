#!/bin/bash
cd board
npm run build-dist
cd ..

if [ "$1" == "-c" ]; then
    python3
    exit
fi

python3 tests.py
