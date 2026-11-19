# Pełny przebieg na wariantach Medium – zestawienie liczb

Maszyna: laptop z Windows 11, Docker Desktop z 8 GB pamięci. Kursy i wyniki zapisywane do lokalnego
kontenera MongoDB w roli Atlasa (`ATLAS_URI=mongodb://mongo-local:27017`).
Wyniki zostały następnie skopiowane do klastra MongoDB Atlas, z którego czyta dashboard.

## Pliki surowe

| Plik | Rozmiar | Wiersze |
|---|---|---|
| `HI-Medium_Trans.csv` | 3 031 783 420 B (2,82 GiB) | 31 898 238 |
| `LI-Medium_Trans.csv` | 2 976 436 978 B (2,77 GiB) | 31 251 483 |
| Razem | 6 008 220 398 B (5,59 GiB) | 63 149 721 |

## Czasy serwisów (pierwszy przebieg)

| Serwis | Czas | Uwagi |
|---|---|---|
| `dataset-extractor` | 292 s | dwa pliki |
| `rates-scraper` | 47 s | 10 stron x-rates i 10 stron CoinMarketCap; dni 1–18 września były już pobrane w trybie próbnym |
| `transactions-etl` | 2 985 s | HI-Medium 24 min 23 s, LI-Medium 25 min 21 s; indeksy istniały wcześniej, więc były aktualizowane w trakcie importu |
| `analytics` | 5 306 s | HI-Medium 43 min, LI-Medium 46 min; jedno przejście po danych wariantu trwa 4–6 min |

Import był liczony 15.11.2026, analityka 16.11.2026 po poprawce wydajności (logi w `medium-first-run.log`).

## Import i jakość danych

| Wariant | Wiersze wczytane | Odrzucone | Załadowane | Dokładne duplikaty (pozostawione) |
|---|---|---|---|---|
| HI-Medium | 31 898 238 | 0 | 31 898 238 | 20 |
| LI-Medium | 31 251 483 | 0 | 31 251 483 | 14 |

## Liczby dokumentów przed i po ponownym uruchomieniu

| Kolekcja | Po pierwszym przebiegu | Po drugim uruchomieniu |
|---|---|---|
| `aml.transactions` (HI-Medium) | 31 898 238 | 31 898 238 |
| `aml.transactions` (LI-Medium) | 31 251 483 | 31 251 483 |
| `aml_results.exchange_rates` | 420 | 420 |
| `aml_results.analysis_results` (Medium) | 10 | 10 |
| `aml_results.dataset_summary` (Medium) | 2 | 2 |

Drugie uruchomienie objęło pobieranie, scraping i import (`medium-rerun.log`). Analityka nadpisuje
swoje dokumenty po identyfikatorze `analiza:wariant`; jej ponowne uruchomienie jest pokazane na
wariancie HI-Small w `hi-small-rerun.log`.

## Rozmiary baz

| Baza | Dane | Na dysku | Indeksy |
|---|---|---|---|
| `aml` (lokalna; 68,2 mln dokumentów razem z HI-Small) | 28,2 GB | 5,99 GB | 3,88 GB |
| `aml_results` (kursy i wyniki; razem z HI-Small) | 134 kB | 188 kB | 131 kB |

Baza z wynikami zajmuje ułamek limitu 512 MB darmowego klastra Atlas M0.
