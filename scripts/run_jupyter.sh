poetry run jt -t onedork
sed -i "s+width: 980px;+width: 97% !important;+g" ~/.jupyter/custom/custom.css
poetry exec jupyter app