/**
 * Classes for the one link or button in a list card that makes the whole card clickable: its
 * `::after` stretches over the card (the card must be `relative`). Other buttons in the card
 * need `relative z-10` to stay clickable on their own.
 */
export const CARD_LINK =
  "cursor-pointer outline-none after:absolute after:inset-0 after:content-[''] " +
  'focus-visible:after:-outline-offset-2 focus-visible:after:outline-2 focus-visible:after:outline-primary-text'

/** The card itself: a soft highlight when the pointer is over it. */
export const CARD = 'relative transition-colors hover:bg-primary/5'
