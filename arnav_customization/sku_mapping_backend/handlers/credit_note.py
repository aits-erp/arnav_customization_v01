def process(doc, method):

    for row in doc.items:

        weight = row.custom_weight
        rate = row.custom_custom_rate
        purity = row.custom_purity

        if weight and rate and purity:

            row.qty = 1
            row.rate = weight * rate * purity