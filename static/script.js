document.getElementById("generateBtn").addEventListener("click", function () {
    let status = document.getElementById("status");
    let generateBtn = document.getElementById("generateBtn");
    let loadingSpinner = document.getElementById("loading");
    let downloadLink = document.getElementById("downloadLink");
    let slidesLink = document.getElementById("openSlidesBtn");

    // Reset previous state
    status.innerText = "Generating presentation... Please wait.";
    generateBtn.disabled = true;
    loadingSpinner.style.display = "block";
    downloadLink.style.display = "none";
    slidesLink.style.display = "none";

    fetch("/generate", { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let pptUrl = data.ppt_url;
                let slidesUrl = data.slides_link;

                downloadLink.href = pptUrl;
                downloadLink.innerText = "Download PPT";
                downloadLink.style.display = "block";

                slidesLink.href = slidesUrl;
                slidesLink.style.display = "block";

                status.innerText = "Presentation ready!";
            } else {
                status.innerText = "Error: " + data.error;
            }
        })
        .catch(error => {
            status.innerText = "Error generating presentation.";
            console.error(error);
        })
        .finally(() => {
            generateBtn.disabled = false;
            loadingSpinner.style.display = "none";
        });
});
