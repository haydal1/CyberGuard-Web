#!/bin/bash
echo "🔄 Updating with YOUR business details..."

# Replace placeholder bank details
sed -i "s/4249996702$(echo -n "YOUR_ACTUAL_ACCOUNT" | sed 's/[&/\]/\\&/g')/g" app.py
sed -i "s/ZenithBank - 4249996702 - Aliyu Egwa Usman/$(echo -n "YOUR_BANK - YOUR_ACCOUNT - YOUR_NAME" | sed 's/[&/\]/\\&/g')/g" app.py
sed -i "s/09031769476/$(echo -n "YOUR_WHATSAPP" | sed 's/[&/\]/\\&/g')/g" app.py

echo "✅ Placeholders updated! Remember to manually edit with your REAL details in app.py"
