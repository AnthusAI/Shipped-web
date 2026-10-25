Feature: Sponsorship is switched off until the site owner switches it on
  The sponsorship units, their style and their script ship in the code but stay off: web/sponsorship.json says enabled false.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: the front page carries no sponsored unit, style or script
    When I open the page "/"
    Then the page does not contain "data-sponsor"
    And the page does not contain "shipped-sponsorship"
    And the page does not contain "Sponsored"

  Scenario: the footer is the publisher line it always was
    When I open the page "/policies/"
    Then the page contains "Published by Anthus AI Solutions."
    And the page does not contain "also sponsors it"

  Scenario: no projected page names a sponsored unit
    Then no projected page contains "sp-card"
