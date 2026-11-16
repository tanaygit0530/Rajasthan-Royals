// Plain-language definitions used by every tooltip on the site.
export const G: Record<string, string> = {
  rating: 'Pressure Rating: runs a player is expected to add per 100 pressure balls next season, compared with what the match situation predicts. 0 = average; higher is better. For bowlers it is runs saved plus wickets (a wicket is worth about 5.6 runs).',
  interval: '80% range: we are 80% confident the true rating lies inside this bar. Ranges were widened until they held up on past seasons.',
  ptop10: 'Chance of being a genuine top-10 player, after accounting for uncertainty. 50% or more = clear; below that the ranking is close to a tie.',
  pressureBall: 'A pressure ball is one where the next delivery can swing the match most (top 25% of balls by expected change in win probability).',
  pressureBalls: 'How many pressure balls the player faced or bowled in the RR data pack, 2022-26. More balls = more evidence.',
  runValue: 'Run value per 100 balls: runs above what the situation predicts, minus about 5.6 runs for each dismissal above expectation (bowlers: the reverse).',
  obsGap: 'Observed pressure vs normal performance. Shown for context only: in our tests this gap did not repeat from one season to the next.',
  price: 'Estimated 2027 auction price range (10th-90th percentile) from past IPL auctions. Auction prices are noisy, so ranges are wide.',
  valuePerCr: 'Value per crore: rating above a replacement-level player divided by the expected price.',
  youth: 'Youth board: players aged 23 or under on 1 April 2027. Buy now / Strong watch / Track depends on the projected next-season level.',
  gap: 'Gap = league benchmark (median of the 10 best eligible players in that role) minus RR\'s best current player in that role. Bigger = weaker.',
  leverage: 'Leverage: how much the next ball can move the win probability, relative to an average ball (1.0).',
  status: 'Availability for the IPL 2027 auction, using trades and retirements to 15 Nov 2026. Retention lists were not yet published.',
  tier: 'Established = 150+ pressure balls; emerging = 40-149 (wider uncertainty).',
}
