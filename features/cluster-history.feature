Feature: The cluster river and the Front changes panel follow the weekly cluster history
  The weekly knowledge run keeps a history of the clusters. The Map draws it as a
  river and the Front says what was born, merged, split or continued since the week
  before. Until the history exists the river stays the dimmed sample.

  Scenario: Without a cluster history the river is the dimmed sample
    Given the Shipped site is built from the fixture content
    When I open the page "/map/"
    Then the page contains "Sample 26-week history, not real data"
    And the page contains "Placeholder"

  Scenario: Without a cluster history the Front has no changes panel
    Given the Shipped site is built from the fixture content
    When I open the page "/"
    Then the page does not contain "front-changes"

  Scenario: With two weeks of history the river is drawn from real counts
    Given the cluster history "two-weeks"
    When the Map river is rendered
    Then the rendering contains "2 weeks of history"
    And the rendering contains "<span>Week of 4 May</span><span>Week of 26 Oct</span>"
    And the rendering does not contain "is-placeholder"

  Scenario: With two weeks of history the Front names what changed with marks and words
    Given the cluster history "two-weeks"
    When the Front changes panel is rendered
    Then the rendering contains "Since the week of 19 Oct"
    And the rendering contains "<b>Merged</b> <span>Agent tooling from Agents and Code models</span>"
    And the rendering contains "<b>Split</b> <span>Voice into Voice cloning and Speech synthesis</span>"
    And the rendering contains "<b>Born</b> <span>1 unnamed</span>"
