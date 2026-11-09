"use strict";

(() => {
  const today = new Date();
  document.querySelectorAll("[data-today-month]").forEach((element) => {
    element.textContent = today.toLocaleDateString("en-US", { month: "short" });
  });
  document.querySelectorAll("[data-today-number]").forEach((element) => {
    element.textContent = String(today.getDate());
  });

  document.querySelectorAll("[data-password-toggle]").forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const input = document.getElementById(toggle.dataset.passwordToggle);
      const showing = input.type === "password";
      input.type = showing ? "text" : "password";
      toggle.textContent = showing ? "Hide" : "Show";
      toggle.setAttribute("aria-pressed", String(showing));
      toggle.setAttribute("aria-label", showing ? "Hide password" : "Show password");
    });
  });

  document.querySelectorAll("[data-account-form]").forEach((form) => {
    const button = form.querySelector("[type=submit]");
    const defaultLabel = button.textContent.trim();
    const restore = () => {
      button.disabled = false;
      button.textContent = defaultLabel;
      form.removeAttribute("aria-busy");
    };
    window.addEventListener("pageshow", restore);
    form.addEventListener("submit", (event) => {
      let firstInvalid = null;
      form.querySelectorAll("input[required]").forEach((input) => {
        const error = document.getElementById(`${input.id}-error`);
        if (!input.value.trim()) {
          if (error) error.hidden = false;
          input.setAttribute("aria-invalid", "true");
          firstInvalid ??= input;
        }
      });
      if (firstInvalid) {
        event.preventDefault();
        firstInvalid.focus();
        return;
      }
      if (event.defaultPrevented) return;
      form.setAttribute("aria-busy", "true");
      button.textContent = form.dataset.submittingLabel;
      button.disabled = true;
    });
    form.querySelectorAll("input").forEach((input) => {
      input.addEventListener("input", () => {
        input.removeAttribute("aria-invalid");
        const error = document.getElementById(`${input.id}-error`);
        if (error) error.hidden = true;
      });
    });
  });

  const localKey = (date) => [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
  const parseDay = (key) => new Date(`${key}T12:00:00`);
  const timeLabel = (date) => date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }).replace(":00", "");
  const statusLabel = (status) => ({ ACCEPETED: "Confirmed", PENDING: "Awaiting reply", REJECTED: "Not accepted", CANCELED: "Canceled" }[status] ?? "Status unavailable");
  const statusClass = (status) => status === "ACCEPETED" ? "status-confirmed" : status === "PENDING" ? "status-pending" : "status-closed";

  document.querySelectorAll("[data-schedule-calendar]").forEach((calendar) => {
    const source = calendar.querySelector("[data-calendar-source]");
    const events = Array.from(source.querySelectorAll("[data-start]")).map((item) => ({
      start: new Date(item.dataset.start),
      end: new Date(item.dataset.end),
      name: item.dataset.name ?? "",
      status: item.dataset.status ?? "ACCEPETED",
    })).filter((event) => !Number.isNaN(event.start.getTime()) && !Number.isNaN(event.end.getTime()));
    const grid = calendar.querySelector("[data-calendar-grid]");
    const heading = calendar.querySelector("[data-month-label]");
    const dayLabel = calendar.querySelector("[data-selected-day]");
    const daySubtitle = calendar.querySelector("[data-day-subtitle]");
    const agenda = calendar.querySelector("[data-agenda-list]");
    const empty = calendar.querySelector("[data-agenda-empty]");
    const picker = calendar.querySelector("[data-date-picker]");
    const announcement = calendar.querySelector("[data-calendar-announcement]");
    const mode = calendar.dataset.scheduleCalendar;
    let selected = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12);
    let month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12);

    // Include appointments spanning midnight on each day they overlap.
    const onDay = (date) => {
      const begin = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const end = new Date(begin);
      end.setDate(end.getDate() + 1);
      return events.filter((event) => event.start < end && event.end > begin).sort((a, b) => a.start - b.start);
    };

    const showAgenda = () => {
      const selectedEvents = onDay(selected);
      dayLabel.textContent = selected.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
      daySubtitle.textContent = mode === "customer" ? "Confirmed booking times" : "Appointments for this day";
      picker.value = localKey(selected);
      agenda.replaceChildren();
      for (const event of selectedEvents) {
        const row = document.createElement("li");
        row.className = "agenda-item";
        const detail = document.createElement("div");
        const time = document.createElement("p");
        time.className = "agenda-time";
        time.textContent = `${timeLabel(event.start)} – ${timeLabel(event.end)}`;
        detail.append(time);
        if (mode === "contractor" && event.name) {
          const name = document.createElement("p");
          name.className = "agenda-name";
          name.textContent = event.name;
          detail.append(name);
        }
        if (localKey(event.start) !== localKey(event.end)) {
          const dates = document.createElement("p");
          dates.className = "agenda-extra";
          dates.textContent = `${event.start.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${event.end.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
          detail.append(dates);
        }
        const status = document.createElement("span");
        status.className = `status ${statusClass(event.status)}`;
        status.textContent = mode === "customer" ? "Booked" : statusLabel(event.status);
        row.append(detail, status);
        agenda.append(row);
      }
      empty.hidden = selectedEvents.length > 0;
      const count = selectedEvents.length;
      const noun = mode === "customer" ? (count === 1 ? "confirmed booking" : "confirmed bookings") : (count === 1 ? "appointment" : "appointments");
      announcement.textContent = `${dayLabel.textContent}. ${count} ${noun}.`;
    };

    const render = () => {
      heading.textContent = month.toLocaleDateString("en-US", { month: "long", year: "numeric" });
      grid.replaceChildren();
      const offset = (month.getDay() + 6) % 7;
      const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
      const cellCount = Math.ceil((offset + days) / 7) * 7;
      for (let index = 0; index < cellCount; index += 1) {
        const date = new Date(month.getFullYear(), month.getMonth(), index - offset + 1, 12);
        const count = onDay(date).length;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "calendar-day";
        button.dataset.day = localKey(date);
        button.textContent = String(date.getDate());
        const isToday = localKey(date) === localKey(today);
        button.classList.toggle("is-outside", date.getMonth() !== month.getMonth());
        button.classList.toggle("is-today", isToday);
        button.classList.toggle("has-events", count > 0);
        button.setAttribute("aria-pressed", String(localKey(date) === localKey(selected)));
        button.tabIndex = localKey(date) === localKey(selected) ? 0 : -1;
        const noun = mode === "customer" ? (count === 1 ? "booked time" : "booked times") : (count === 1 ? "appointment" : "appointments");
        button.setAttribute("aria-label", `${date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}${isToday ? ", today" : ""}${count ? `, ${count} ${noun}` : ""}`);
        button.addEventListener("click", () => {
          selected = date;
          if (date.getMonth() !== month.getMonth()) month = new Date(date.getFullYear(), date.getMonth(), 1, 12);
          render();
          grid.querySelector(`[data-day="${localKey(selected)}"]`)?.focus({ preventScroll: true });
        });
        button.addEventListener("keydown", (event) => {
          const increments = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
          if (!(event.key in increments)) return;
          event.preventDefault();
          selected = new Date(date);
          selected.setDate(selected.getDate() + increments[event.key]);
          month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12);
          render();
          grid.querySelector(`[data-day="${localKey(selected)}"]`)?.focus({ preventScroll: true });
        });
        grid.append(button);
      }
      showAgenda();
    };

    calendar.querySelectorAll("[data-month-step]").forEach((button) => {
      button.addEventListener("click", () => {
        month = new Date(month.getFullYear(), month.getMonth() + Number(button.dataset.monthStep), 1, 12);
        selected = new Date(month);
        render();
      });
    });
    calendar.querySelector("[data-calendar-today]").addEventListener("click", () => {
      selected = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12);
      month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12);
      render();
    });
    picker.addEventListener("change", () => {
      const date = parseDay(picker.value);
      if (Number.isNaN(date.getTime())) return;
      selected = date;
      month = new Date(date.getFullYear(), date.getMonth(), 1, 12);
      render();
    });
    source.hidden = true;
    calendar.querySelector("[data-calendar-ui]").hidden = false;
    render();
  });

  document.querySelectorAll("[data-filter-section]").forEach((section) => {
    const buttons = section.querySelectorAll("[data-appointment-filter]");
    const rows = section.querySelectorAll("[data-appointment-status]");
    const empty = section.querySelector("[data-filter-empty]");
    const announcement = section.querySelector("[data-filter-announcement]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.appointmentFilter;
        let visible = 0;
        rows.forEach((row) => {
          const status = row.dataset.appointmentStatus;
          const matches = filter === "all" || status === filter || (filter === "closed" && ["REJECTED", "CANCELED"].includes(status));
          row.hidden = !matches;
          if (matches) visible += 1;
        });
        buttons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
        empty.hidden = visible > 0;
        announcement.textContent = `${visible} appointments shown. Filter: ${button.textContent.trim()}.`;
      });
    });
  });
})();
