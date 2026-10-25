Feature: Sponsored units are disclosed and kept out of editorial controls
  Anthus sponsors Shipped. Its units are rounded, say "Sponsored", carry a diamond and name Anthus, and stay out of votes, proposals and policies.

  Background:
    Given the Shipped site is built from the fixture content

  Scenario: the front page carries the sponsor bar and labelled units
    When I open the page "/"
    Then the page contains "sp-bar-presenter"
    And the page contains "Sponsored"
    And the page contains "shipped-sponsorship"

  Scenario: the footer names the publisher as the sponsor
    When I open the page "/policies/"
    Then the page contains "Published by Anthus AI Solutions, which also sponsors it."
    And the page contains "/policies/#sponsorship"

  Scenario: the policies page carries the bar and no other unit
    When I open the page "/policies/"
    Then the page contains "sp-bar-presenter"
    And the page does not contain "sp-banner-copy"
    And the page does not contain "sp-card-pitch"

  Scenario: the proposals page carries the bar and no other unit
    When I open the page "/proposals/"
    Then the page contains "sp-bar-presenter"
    And the page does not contain "sp-item"
    And the page does not contain "sp-note-body"
