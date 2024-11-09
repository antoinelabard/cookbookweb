# Add the canarytokens to each html file
find recettes -name "*.html" -type f -exec sed -i 's/<div class="markdown-preview-sizer markdown-preview-section">/<div class="markdown-preview-sizer markdown-preview-section kazes"><img src="http:\/\/canarytokens.com\/sw5uvmb82rxizmwhubn225gvr">/g' {} +
find catégories -name "*.html" -type f -exec sed -i 's/<div class="markdown-preview-sizer markdown-preview-section">/<div class="markdown-preview-sizer markdown-preview-section kazsqd"><img src="http:\/\/canarytokens.com\/t5w0b10daouy2fkd23kgkm6fc">/g' {} +
find . -name "index.html" -type f -exec sed -i 's/<div class="markdown-preview-sizer markdown-preview-section">/<div class="markdown-preview-sizer markdown-preview-section kxcdw"><img src="http:\/\/canarytokens.com\/ijpluamg2u65kgvhs62jaeykj">/g' {} +
find . -name "menu-de-la-semaine.html" -type f -exec sed -i 's/<div class="markdown-preview-sizer markdown-preview-section">/<div class="markdown-preview-sizer markdown-preview-section ezrdfg"><img src="http:\/\/canarytokens.com\/t5w0b10daouy2fkd23kgkm6fc">/g' {} +

# Display the recipes front-matter
find . -name "*.html" -type f -exec sed -i 's/<pre/<pre style="display: visible !important;overflow: visible !important;min-height: auto !important;"/g' {} +

# Upload the website to GitHub
git add .
git commit -m "update website"
git push origin main
