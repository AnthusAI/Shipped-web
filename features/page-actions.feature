Feature: Pages offer their sharing actions as icons
  Readers can view a page as Markdown, post it to X or Reddit, or share it, from a row of
  labelled icons. The older text buttons are gone.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: The map page has labelled icons and no text buttons
    When I open the page "/map/"
    Then the page contains "markus-page-actions-icons"
    And the page contains "View as Markdown"
    And the page contains "Post on X"
    And the page contains "Post on Reddit"
    And the page does not contain ">Copy Markdown</button>"
