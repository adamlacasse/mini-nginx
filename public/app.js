const button = document.querySelector("#load-api");
const output = document.querySelector("#output");

button.addEventListener("click", async () => {
  output.textContent = "Loading...";

  try {
    const response = await fetch("/api/hello");
    const data = await response.json();

    output.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    output.textContent = String(err);
  }
});
