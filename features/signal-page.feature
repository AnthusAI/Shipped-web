Feature: A signal page shows the status, the evidence, the map and the ratings
  Every item is a signal. Its page says its status and who stamped it, shows the primary
  evidence and where it sits on the map, and rates it on four dimensions with readers and
  editors shown apart. Items that still carry the old score keys never show them.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: A signal page rates the four dimensions
    When I open the page "/open-weights/fixture-full-contract/"
    Then the page contains "Primary evidence"
    And the page contains "On the map"
    And the page contains "Ratings"
    And the page contains "Does it do a real job well?"
    And the page contains "Not yet rated"
    And the page does not contain "this week"

  Scenario: An item with the old score keys never shows them
    When I open the page "/decisions/fixture-router-two/"
    Then the page contains "Not yet rated"
    And the page does not contain "<b>Notable</b>"
    And the page does not contain "<b>Novel</b>"

  Scenario: Board rows carry no score columns
    When I open the page "/new/"
    Then the page does not contain "board-dimensions"
    And the page contains "board-section"
