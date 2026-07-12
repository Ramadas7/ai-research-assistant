# Evaluation Report — 2026-07-12 23:29

- Test cases: 9
- Retrieval hit rate @5: 22%
- Mean Reciprocal Rank: 0.17
- Avg faithfulness: 4.0/5
- Avg relevancy: 2.8/5

| Question | Hit@5 | Rank | Expected | Retrieved | Faithfulness | Relevancy | Notes |
|---|---|---|---|---|---|---|---|
| What is this pdf about? | NO | - | 10 | [216, 4, 195, 218, 122] | 5 | 0 |  |
| Are there any characters in this book, if any who are they? | NO | - | 17 | [195, 198, 9, 4, 170] | 3 | 1 |  |
| Explain this pdf in some breif key points. | NO | - | 9 | [216, 58, 72, 198, 198] | 5 | 4 |  |
| Who were the 2 fathers mentioned in the book? | YES | 2 | 10 | [11, 10, 13, 10, 9] | 5 | 4 | (judge response wasn't valid JSON, salvaged with regex) |
| Who was the rich dad? | NO | - | 22 | [2, 1, 38, 17, 6] | 4 | 3 |  |
| Give me the list of all the lessons mentioned in this pdf. | NO | - | 9 | [219, 16, 190, 182, 203] | 0 | 0 |  |
| Can you explain the difference between Poor Dad's Financial Statement and Rich Dad's Financial Statement? | YES | 1 | 71 | [71, 12, 57, 59, 2] | 4 | 5 | The AI's answer closely follows the reference answer, capturing key points about the similarities and differences between Poor Dad's and Rich Dad's financial statements. |
| Summarize this pdf. | NO | - | 178 | [216, 71, 71, 161, 198] | 5 | 4 | The AI's answer closely mirrors the reference, condensing key points from the PDF into a coherent summary while omitting some minor details and specific quotes. |
| Explain CASHFLOW Quadrant | NO | - | 181 | [213, 214, 219, 216, 102] | 5 | 4 | The answer accurately explains the concept of CASHFLOW Quadrant as described in Robert Kiyosaki's book, but lacks details and a clear connection to the reference provided. |