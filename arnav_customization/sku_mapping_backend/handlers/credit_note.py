def process(doc, method):

    for row in doc.items:

        weight = row.get("custom_weight")
        rate = row.get("custom_custom_rate") or row.get("rate")
        purity = row.get("custom_purity")

        if weight is not None and rate is not None and purity is not None:
            row.qty = 1
            row.rate = weight * rate * purity

# def process(doc, method):

#     for row in doc.items:

#         weight = row.custom_weight
#         rate = row.custom_custom_rate
#         purity = row.custom_purity

#         if weight and rate and purity:

#             row.qty = 1
#             row.rate = weight * rate * purity