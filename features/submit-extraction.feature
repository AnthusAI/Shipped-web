Feature: The Submit page shows what the map pulled out of a reader's own link
  After a reader sends a link, AI reads it and pulls out the model, the maker and
  the task. Only that reader sees the result, and they confirm it or fix it. Until
  they have a submission the section stays the dimmed design with one Placeholder tag.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: Before a submission the section is the dimmed design
    When I open the page "/submit/"
    Then the page contains "Confirm what the map pulled out"
    And the page contains "data-extraction-live"
    And the page contains "Placeholder"

  Scenario: The Submit page loads the confirm script and other pages do not
    When I open the page "/submit/"
    Then the page contains "/assets/shipped-extraction.js"
    When I open the page "/"
    Then the page does not contain "/assets/shipped-extraction.js"
