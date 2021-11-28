# CryptoAPIWrapper

## About
This repository contains a solution to following Synthesia coding challenge
https://www.notion.so/Synthesia-Backend-Tech-Challenge-52a82f750aed436fbefcf4d8263a97be

Let's call the API implemented in this repo the "Wrapping API".

## Language and framework
The API is implemented in Python3 using Flask library.

## Algorithm
- every call to the Wrapping API first checks if requested message is in the shelve
  - in such case, the Wrapping API returns what it found in the shelve
- otherwise the message is passed on to Synthesia API
- if 200 is received from Synthesia API, a success response with the signed message is immediately returned to the client
- in case of different status code than 200 is received:
  - response is stored in shelve
  - message is put at the end of the request processing queue
- every 6 seconds, message from the head of the queue is retried against Synthesia crypto sign API

## Details
- the Wrapping API always returns 200
- in case Synthesia API doesn't return 200 code, Wrapping API calculates approximate retry time for given message in seconds
- this can be useful for the client to schedule the retry on it's end using this information
- I considered using Websocket to keep a connection live and push notification to client once message signature was ready
    - I decided to leave it out from this basic version, as I'd likely need more information about the number and types of clients that would be calling the Wrapping API to decide if Websockets were good fit for the use case

## Request and response format

### Request

Should be identical to Synthesia Crypto API.

### Response

Example response containing message signature:
```
{
  "last_status_code": 200, 
  "success": true, 
  "value": "En5u4Y_0KagCALQKh5rm36qzBzuiQGLCLL6d4161ivOrSeXNR_lN65mdd5Nw4ShgT6G5Tr8ZhewwOSwJQ5fdQHkph39bfrTu4sCIPafSehnnmrJ9eUs4cemZPVcBay_zlougEUWzBCCtvuFQBoz7bF4PFVLtAojjS9x-5EVZce_OyVN0no_Y3E09N3PeTcMPfIMgOOu-AVWqNdv-YByCXOtdCkze-5E_Wv8Y0QbrzhIoyZFPHxmXP6f5h4yUDx5qbqhNyIVOdOIEFJMjtnkHHmjsia9aD_JiCsHL3ULU01tbFefZBII31L0vED12FfKbyD52fphhAnxviyZaRRVXpA=="
}
```

Example response containing waiting to be retried:
```
{
  "last_status_code": 502, 
  "retry_in_seconds": 36, 
  "success": false, 
  "value": "Error 502: Failed to sign message due to simulated service degradation.\n"
}
```