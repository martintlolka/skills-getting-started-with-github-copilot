document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  let latestActivitiesRequest = 0;
  let pendingRemovalFocus = null;

  // Function to fetch activities from API
  async function fetchActivities() {
    const requestId = ++latestActivitiesRequest;
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities");
      }
      const activities = await response.json();
      if (requestId !== latestActivitiesRequest) return;

      const activeElement = document.activeElement;
      const focusedCard = activeElement?.closest(".activity-card");
      const focusedButtons = focusedCard
        ? Array.from(focusedCard.querySelectorAll(".participant-remove"))
        : [];
      const focusToRestore = focusedCard
        ? {
            activity: focusedCard.querySelector("h4").textContent,
            email: activeElement.closest("li")?.querySelector("span")?.textContent,
            index: focusedButtons.indexOf(activeElement),
          }
        : activeElement === document.body ? pendingRemovalFocus : null;
      pendingRemovalFocus = null;
      let focusElement = null;

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.querySelectorAll("option:not(:first-child)").forEach((option) => {
        option.remove();
      });

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        const title = document.createElement("h4");
        title.textContent = name;
        title.tabIndex = -1;

        const description = document.createElement("p");
        description.textContent = details.description;

        const schedule = document.createElement("p");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule: ";
        schedule.append(scheduleLabel, document.createTextNode(details.schedule));

        const availability = document.createElement("p");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability: ";
        availability.append(
          availabilityLabel,
          document.createTextNode(`${spotsLeft} spots left`)
        );

        const participantsHeading = document.createElement("h5");
        participantsHeading.textContent = "Participants";

        const participantsList = document.createElement("ul");
        participantsList.className = "participant-list";

        if (details.participants.length === 0) {
          const emptyItem = document.createElement("li");
          emptyItem.textContent = "No participants yet";
          emptyItem.className = "no-participants";
          participantsList.appendChild(emptyItem);
        } else {
          details.participants.forEach((email) => {
            const participantItem = document.createElement("li");
            const participantEmail = document.createElement("span");
            participantEmail.textContent = email;

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "participant-remove";
            removeButton.textContent = "🗑";
            removeButton.setAttribute("aria-label", `Unregister ${email}`);
            removeButton.title = `Unregister ${email}`;

            participantItem.append(participantEmail, removeButton);
            participantsList.appendChild(participantItem);
          });
        }

        activityCard.append(
          title,
          description,
          schedule,
          availability,
          participantsHeading,
          participantsList
        );

        activitiesList.appendChild(activityCard);

        if (focusToRestore?.activity === name) {
          const buttons = Array.from(
            activityCard.querySelectorAll(".participant-remove")
          );
          focusElement = buttons.find(
            (button) => button.closest("li").querySelector("span").textContent === focusToRestore.email
          ) || buttons[Math.min(focusToRestore.index, buttons.length - 1)] || title;
        }

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
      focusElement?.focus();
    } catch (error) {
      if (requestId === latestActivitiesRequest) {
        activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      }
      console.error("Error fetching activities:", error);
    }
  }

  // Handle participant removal from activity cards
  activitiesList.addEventListener("click", async (event) => {
    const removeButton = event.target.closest(".participant-remove");
    if (!removeButton) return;

    const participantItem = removeButton.closest("li");
    const email = participantItem.querySelector("span").textContent;
    const activityCard = removeButton.closest(".activity-card");
    const activity = activityCard.querySelector("h4").textContent;
    const focusAfterRemoval = document.activeElement === removeButton
      ? {
          activity,
          email,
          index: Array.from(
            activityCard.querySelectorAll(".participant-remove")
          ).indexOf(removeButton),
        }
      : null;
    if (focusAfterRemoval) pendingRemovalFocus = focusAfterRemoval;
    removeButton.disabled = true;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to unregister participant");
      }

      await fetchActivities();
    } catch (error) {
      removeButton.disabled = false;
      if (pendingRemovalFocus === focusAfterRemoval) pendingRemovalFocus = null;
      if (focusAfterRemoval && document.activeElement === document.body && removeButton.isConnected) {
        removeButton.focus();
      }
      console.error("Error unregistering participant:", error);
      messageDiv.textContent = error.message || "Failed to unregister participant.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
    }
  });

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();
        await fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  fetchActivities();
});
