Feature: Approved stories replace the story placeholders
  Stories are AI-drafted and editor-approved. Only approved stories render. Until a
  section or the front page has one, the placeholder stays in its slot.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: An approved story page shows the provenance trail and the cited signals
    When I open the page "/stories/fixture-story-newest/"
    Then the page contains "Drafted by AI"
    And the page contains "Approved by <b>fixture-editor</b>"
    And the page contains "Signals cited"
    And the page contains "What this changes on the map"
    And the page does not contain "readers steered it"

  Scenario: A pending story has no page
    Then the page "/stories/fixture-story-pending/" does not exist

  Scenario: A pending story appears nowhere
    Then no projected page contains "PENDING-STORY-MUST-NOT-RENDER"
    And no projected page contains "PENDING-STANDFIRST-MUST-NOT-RENDER"

  Scenario: The front page leads with the newest approved story
    When I open the page "/"
    Then the page contains "Fixture story: guard models now name their parents"
    And the page contains "Fixture story: open weights for fictional speech"
    And the page does not contain "[Story headline]"

  Scenario: A section with no approved story keeps the placeholder lead
    When I open the page "/shipped/"
    Then the page contains "The lead story for this section will appear here"

  Scenario: A section with an approved story leads with it
    When I open the page "/decisions/"
    Then the page contains "Fixture story: guard models now name their parents"
    And the page does not contain "The lead story for this section will appear here"
