# Data Dictionary

This document provides a data dictionary based on the profiling of raw Olist tables. Business meanings have been drafted for review.

## 1. Customers (`olist_customers_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `customer_id` | object | 0.0% | Order-level customer identifier. A unique ID assigned to each order. |
| `customer_unique_id` | object | 0.0% | Person-level identifier. A single person may have multiple `customer_id`s if they made multiple purchases. |
| `customer_zip_code_prefix` | object | 0.0% | First 5 digits of the customer's zip code. |
| `customer_city` | object | 0.0% | Customer's city name. |
| `customer_state` | object | 0.0% | Customer's state code (UF). |

## 2. Geolocation (`olist_geolocation_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `geolocation_zip_code_prefix` | object | 0.0% | First 5 digits of the zip code. |
| `geolocation_lat` | float64 | 0.0% | Latitude coordinate. |
| `geolocation_lng` | float64 | 0.0% | Longitude coordinate. |
| `geolocation_city` | object | 0.0% | City name. |
| `geolocation_state` | object | 0.0% | State code (UF). |

## 3. Order Items (`olist_order_items_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `order_id` | object | 0.0% | Unique identifier of the order. |
| `order_item_id` | object | 0.0% | Sequential number identifying number of items included in the same order. |
| `product_id` | object | 0.0% | Unique identifier of the product. |
| `seller_id` | object | 0.0% | Unique identifier of the seller. |
| `shipping_limit_date` | object | 0.0% | Seller shipping limit date for handling the order. |
| `price` | float64 | 0.0% | Item price (excluding freight). |
| `freight_value` | float64 | 0.0% | Freight cost apportioned to the item (if an order has multiple items, freight value is split). |

## 4. Order Payments (`olist_order_payments_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `order_id` | object | 0.0% | Unique identifier of the order. |
| `payment_sequential` | int64 | 0.0% | Sequence number for cases where an order is paid with more than one payment method. |
| `payment_type` | object | 0.0% | Method of payment chosen by the customer (e.g., credit_card, boleto, voucher). |
| `payment_installments` | int64 | 0.0% | Number of installments chosen by the customer. |
| `payment_value` | float64 | 0.0% | Transaction value. |

## 5. Order Reviews (`olist_order_reviews_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `review_id` | object | 0.0% | Unique identifier of the review. |
| `order_id` | object | 0.0% | Unique identifier of the order. |
| `review_score` | int64 | 0.0% | Satisfaction score given by the customer, ranging from 1 to 5. |
| `review_comment_title` | object | 88.34% | Comment title left by the customer. |
| `review_comment_message` | object | 58.7% | Comment message left by the customer. |
| `review_creation_date` | object | 0.0% | Date in which the satisfaction survey was sent to the customer. |
| `review_answer_timestamp` | object | 0.0% | Timestamp of the satisfaction survey answer. |

## 6. Orders (`olist_orders_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `order_id` | object | 0.0% | Unique identifier of the order. |
| `customer_id` | object | 0.0% | Key to the customer dataset (each order has a unique customer_id). |
| `order_status` | object | 0.0% | Reference to the order status (e.g., delivered, shipped, canceled). |
| `order_purchase_timestamp` | object | 0.0% | Timestamp of the purchase. |
| `order_approved_at` | object | 0.16% | Timestamp of the payment approval. |
| `order_delivered_carrier_date` | object | 1.79% | Timestamp of order posting (when handed to carrier). |
| `order_delivered_customer_date` | object | 2.98% | Actual date of delivery to the customer. |
| `order_estimated_delivery_date` | object | 0.0% | Estimated delivery date provided to the customer at purchase. |

## 7. Products (`olist_products_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `product_id` | object | 0.0% | Unique identifier of the product. |
| `product_category_name` | object | 1.85% | Root category of the product, in Portuguese. |
| `product_name_lenght` | float64 | 1.85% | Number of characters in the product name. |
| `product_description_lenght` | float64 | 1.85% | Number of characters in the product description. |
| `product_photos_qty` | float64 | 1.85% | Number of photos published for the product. |
| `product_weight_g` | float64 | 0.01% | Product weight measured in grams. |
| `product_length_cm` | float64 | 0.01% | Product length measured in centimeters. |
| `product_height_cm` | float64 | 0.01% | Product height measured in centimeters. |
| `product_width_cm` | float64 | 0.01% | Product width measured in centimeters. |

## 8. Sellers (`olist_sellers_dataset.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `seller_id` | object | 0.0% | Unique identifier of the seller. |
| `seller_zip_code_prefix` | object | 0.0% | First 5 digits of the seller's zip code. |
| `seller_city` | object | 0.0% | Seller's city name. |
| `seller_state` | object | 0.0% | Seller's state code (UF). |

## 9. Translation (`product_category_name_translation.csv`)

| Column | Type | Null % | Business Meaning |
|---|---|---|---|
| `product_category_name` | object | 0.0% | Category name in Portuguese. |
| `product_category_name_english` | object | 0.0% | Category name translated to English. |
