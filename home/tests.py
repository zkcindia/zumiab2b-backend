from django.test import TestCase

# Create your tests here.



@api_view(["GET"])
def product_api(request, slug=None):

    if request.method == "GET":

        display, _ = DisplaySetting.objects.get_or_create(id=1)

        # ================= SINGLE PRODUCT =================
        if slug:
            try:
                product = Product.objects.select_related(
                    "brand",
                    "category"
                ).get(slug=slug)

                images = ProductImage.objects.filter(product=product)

                product_data = {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "status": product.status,
                    "min_order_qty": product.min_order_qty,
                    "is_active": product.is_active,

                    "images": [
                        {
                            "id": img.id,
                            "image": request.build_absolute_uri(img.image.url)
                        }
                        for img in images
                    ]
                }


                if display.item_code:
                    product_data["item_code"] = product.item_code


                if display.mrp:
                    product_data["mrp"] = str(product.mrp)


                if display.retail:
                    product_data["retail"] = str(product.retail)


                if display.b2b:
                    product_data["b2b"] = str(product.b2b)


                if display.sku:
                    product_data["sku"] = product.sku


                if display.stock_quantity:
                    product_data["stock_quantity"] = product.stock_quantity


                if display.brand:
                    product_data["brand"] = (
                        {
                            "id": product.brand.id,
                            "name": product.brand.name
                        }
                        if product.brand else None
                    )


                if display.description:
                    product_data["description"] = product.description


                product_data["category"] = (
                    {
                        "id": product.category.id,
                        "name": product.category.name
                    }
                    if product.category else None
                )


                return JsonResponse({
                    "status": True,
                    "data": product_data
                })


            except Product.DoesNotExist:

                return JsonResponse({
                    "status": False,
                    "message": "Product not found"
                }, status=404)



        # ================= PRODUCT LIST =================

        limit = int(request.GET.get("limit", 10))
        offset = int(request.GET.get("offset", 0))


        products = Product.objects.select_related(
            "brand",
            "category"
        ).filter(
            status="Publish"
        ).order_by("-id")


        total = products.count()

        page_data = products[offset:offset + limit]


        result = []


        for product in page_data:

            images = ProductImage.objects.filter(product=product)


            product_data = {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "status": product.status,
                "min_order_qty": product.min_order_qty,

                "images": [
                    {
                        "id": img.id,
                        "image": request.build_absolute_uri(img.image.url)
                    }
                    for img in images
                ]
            }


            if display.item_code:
                product_data["item_code"] = product.item_code


            if display.mrp:
                product_data["mrp"] = str(product.mrp)


            if display.retail:
                product_data["retail"] = str(product.retail)


            if display.b2b:
                product_data["b2b"] = str(product.b2b)


            if display.sku:
                product_data["sku"] = product.sku


            if display.stock_quantity:
                product_data["stock_quantity"] = product.stock_quantity


            if display.brand:
                product_data["brand"] = (
                    {
                        "id": product.brand.id,
                        "name": product.brand.name
                    }
                    if product.brand else None
                )


            if display.description:
                product_data["description"] = product.description


            product_data["category"] = (
                {
                    "id": product.category.id,
                    "name": product.category.name
                }
                if product.category else None
            )


            result.append(product_data)



        return JsonResponse({
            "status": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
            "data": result
        })