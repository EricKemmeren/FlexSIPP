module load 2026
module load python/3.13

cd /home/<netid>/FlexSIPP

rm -rf .venv
python -m venv .venv
source .venv/bin/activate

pip download . -d /home/<netid>/FlexSIPP/wheelhouse

pip download meson meson-python ninja -d /home/<netid>/FlexSIPP/wheelhouse

pip download contourpy cycler fonttools kiwisolver matplotlib numpy packaging pillow pyparsing python-dateutil python-rapidjson six sortedcontainers tqdm jinja2 patchelf -d /home/<netid>/FlexSIPP/wheelhouse
