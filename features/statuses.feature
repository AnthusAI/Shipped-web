Feature: Items carry one of three neutral statuses
  Every item is Available, Verified or Announced. Available means anyone can use it
  today. Verified means it is Available and an editor checked the evidence. Announced
  means it is claimed, not yet usable or not yet confirmed. Each status is a mark
  and a word, so it never depends on colour alone.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: The scoring data names the three statuses
    Then the scoring data names the verdicts available, verified, announced

  Scenario: An item an editor verified shows the Verified mark and word
    When I open the page "/open-weights/fixture-full-contract/"
    Then the page shows the status "Verified" as a mark with its word
    And the page contains "Verified by the fixture editor"

  Scenario: An item anyone can use shows the Available mark and word
    When I open the page "/decisions/fixture-guard-one/"
    Then the page shows the status "Available" as a mark with its word

  Scenario: An item still only claimed shows the Announced mark and word
    When I open the page "/decisions/fixture-router-two/"
    Then the page shows the status "Announced" as a mark with its word

  Scenario: The marks differ in shape as well as in word
    When I open the page "/"
    Then the three status marks use three different shapes

  Scenario: The row key on the New page explains the three statuses
    When I open the page "/new/"
    Then the rail key lists Available, Verified and Announced in that order
    And the page contains "Anyone can use it today."
    And the page contains "Claimed, not yet usable or not yet confirmed."

  Scenario: The submit page explains the same three statuses
    When I open the page "/submit/"
    Then the page contains "Anyone can use it today."
    And the page contains "New signals start as Announced"

  Scenario: The old status words are gone from every page
    When I open the page "/new/"
    Then no page uses "Shipped" as a status
    And no page uses "Pending" as a status
    And no page uses "Vapor" as a status
