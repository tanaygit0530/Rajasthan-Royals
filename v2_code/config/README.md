# Config (editable, public information only)

- `retentions_2027.csv` – IPL 2027 retained / released players per team, as published on 17 Nov 2026
  (Willow Sports via Yahoo Sports; RR list confirmed on rajasthanroyals.com). Names are normalised to the spelling used
  in our player register (e.g. "Varun Chakaravarthy" -> "Varun Chakravarthy", "Blessing Muzarbani" -> "Blessing
  Muzarabani", "AM Ghazanfar" -> "Allah Ghazanfar", "R. Sai Kishore" -> "Sai Kishore", "Nitish Kumar Reddy" ->
  "Nitish Reddy", "V Vyshak" -> "Vyshak Vijaykumar", "Pat Cummins" -> "Patrick Cummins", "Will Jacks" -> "William Jacks", "Raj Angad Bawa" -> "Raj Bawa", "Rasikh Dar" -> "Rasikh Salam", "Matt Short" -> "Matthew Short"). The article omits players traded before the deadline
  (e.g. Natarajan, Livingstone, Edwards, Khaleel, Ellis); those are covered by the trade table in s13_final.py.
- `teams_2027.csv` – remaining purse, slots and overseas slots per team after retentions (same source).
Edit these files and re-run `s13_final.py --quick` onward to refresh every status and list.
