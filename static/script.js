document.getElementById("generateBtn").addEventListener("click", function () {
    let status = document.getElementById("status");
    status.innerText = "Generating presentation... Please wait.";

    fetch("/generate", { method: "POST" })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let pptUrl = data.ppt_url;
                let slidesUrl = data.slides_link;

                // Update download link
                let downloadLink = document.getElementById("downloadLink");
                downloadLink.href = pptUrl;
                downloadLink.innerText = "Download PPT";
                downloadLink.style.display = "block";

                // Show "Open in Google Slides" button
                let slidesLink = document.getElementById("openSlidesBtn");
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
        });
});
