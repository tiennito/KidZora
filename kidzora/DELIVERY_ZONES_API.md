# Delivery Zones API

All endpoints require an authenticated admin user.

## Create

`POST /delivery-zones`

Request:

```json
{
  "locationName": "Cebu City",
  "deliveryFee": 50
}
```

Response `201`:

```json
{
  "data": {
    "id": "uuid",
    "locationName": "Cebu City",
    "deliveryFee": 50.0,
    "createdAt": "2026-05-19T00:00:00",
    "updatedAt": "2026-05-19T00:00:00"
  }
}
```

## List

`GET /delivery-zones`

Response:

```json
{
  "data": [
    {
      "id": "uuid",
      "locationName": "Cebu City",
      "deliveryFee": 50.0,
      "createdAt": "2026-05-19T00:00:00",
      "updatedAt": "2026-05-19T00:00:00"
    }
  ]
}
```

## View

`GET /delivery-zones/{id}`

## Update

`PUT /delivery-zones/{id}`

Request:

```json
{
  "locationName": "Manila",
  "deliveryFee": 80
}
```

## Delete

`DELETE /delivery-zones/{id}`

Response:

```json
{ "ok": true }
```

## Checkout Fee Calculation

`POST /buyer/checkout/delivery-fee`

Request:

```json
{
  "city": "Cebu City",
  "province": "Cebu",
  "region": "Region VII"
}
```

Response:

```json
{
  "fee": 50.0,
  "matched": true,
  "matchType": "city",
  "locationName": "Cebu City",
  "fallback": false,
  "region": "Region VII"
}
```

Matching priority is `city`, then `province`, then `region`. If none match, the system uses `platform_settings.default_delivery_fee`.
