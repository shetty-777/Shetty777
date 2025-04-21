// script.js
if ('fonts' in document) {
  Promise.all([
    document.fonts.load('1em Roboto'),
    document.fonts.load('700 1em Roboto'),
    document.fonts.load('italic 1em Roboto'),
    document.fonts.load('italic 700 1em Roboto')
  ]).then(_ => () => {document.documentElement.classList.add('fonts-loaded')})
}





const themeSwitcher = document.getElementById('themeSwitcher');
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    themeSwitcher.checked = newTheme === 'dark';
    localStorage.setItem('theme', newTheme);
}
themeSwitcher.addEventListener('change', toggleTheme);
const storedTheme = localStorage.getItem('theme');
if (storedTheme) {
    document.documentElement.setAttribute('data-bs-theme', storedTheme);
    themeSwitcher.checked = storedTheme === 'dark';
}





document.addEventListener("DOMContentLoaded", function(){

  autohide = document.querySelector('.autohide');
  
  navbar_height = document.querySelector('.navbar').offsetHeight;
  document.body.style.paddingTop = navbar_height + 'px';

  if(autohide){
    var last_scroll_top = 0;
    window.addEventListener('scroll', function() {
          let scroll_top = window.scrollY;
          if(scroll_top < last_scroll_top) {
              autohide.classList.remove('scrolled-down');
              autohide.classList.add('scrolled-up');
          }
          else {
              autohide.classList.remove('scrolled-up');
              autohide.classList.add('scrolled-down');
          }
          last_scroll_top = scroll_top;}); }});



$(() => {
  $('abbr[data-title]').each(function () {
      const data_title = $(this).attr('data-title');
      $(this)
          .attr('data-bs-toggle', 'tooltip')
          .attr('data-bs-title', data_title)
          .attr('data-bs-placement', 'bottom')
          .attr('data-bs-custom-class', 'themed-tooltip');
  });

  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
});


const confirmationModal = document.getElementById('confirmationModal')
if (confirmationModal) {
  confirmationModal.addEventListener('show.bs.modal', event => {
    // Button that triggered the modal
    const button = event.relatedTarget
    // Extract info from data-bs-* attributes
    const delsubname = button.getAttribute('data-bs-delsubname')
    const delsubid = button.getAttribute('data-bs-delsubid')

    const modalBodyp = confirmationModal.querySelector('.modal-body p')
    const modalBodybutton = confirmationModal.querySelector('.modal-footer a')

    modalBodyp.textContent = `Are you sure you want to delete ${delsubname} from the list of subscribers?`
    modalBodybutton.dataset.subscriberId = `${delsubid}`
  })
}
const confirmationModalP = document.getElementById('confirmationModalP')
if (confirmationModalP) {
  confirmationModalP.addEventListener('show.bs.modal', event => {
    // Button that triggered the modal
    const button = event.relatedTarget
    // Extract info from data-bs-* attributes
    const delposturl = button.getAttribute('data-bs-delposturl')
    const delpostid = button.getAttribute('data-bs-delpostid')

    const modalBodyp = confirmationModalP.querySelector('.modal-body p')
    const modalBodybutton = confirmationModalP.querySelector('.modal-footer a')

    modalBodyp.innerHTML = `You are about to delete the post with the URL: <br> <i><u>${delposturl}</u></i> <br> This will also delete all the media files present in the post [images and audios].<br><br><b>ARE YOU SURE YOU WANT TO PROCEED?</b>`
    modalBodybutton.dataset.postId = `${delpostid}`
  })
}





$(document).ready(function() {
  $(document).on('click', '#mark-post', function(event) {
      event.preventDefault();
      var postid = $(this).data('postid');
      var userid = $(this).data('userid');

      $.ajax({
          type: 'POST',
          url: '/mark_post/' + userid + '/' + postid,
          success: function(response) {
              if (response.status === 'success') {
                  // Hide tooltip
                  $('#mark-post').tooltip('dispose');
                  // Replace button and bind click event
                  $('#mark-post').replaceWith('<a class="text-body-secondary m-3" type="button" id="unmark-post" data-postid="' + postid + '" data-userid="' + userid + '" data-bs-custom-class="themed-tooltip" data-bs-toggle="tooltip" data-bs-title="This post is marked"><i class="bi bi-bookmark-check-fill" style="font-size:1.5rem"></i></a>');
                  // Initialize tooltip on new button
                  $('#unmark-post').tooltip();
              } else {
                  alert(response.message);
              }
          }
      });
  });

  $(document).on('click', '#unmark-post', function(event) {
      event.preventDefault();
      var postid = $(this).data('postid');
      var userid = $(this).data('userid');

      $.ajax({
          type: 'POST',
          url: '/unmark_post/' + userid + '/' + postid,
          success: function(response) {
              if (response.status === 'success') {
                  // Hide tooltip
                  $('#unmark-post').tooltip('dispose');
                  // Replace button and bind click event
                  $('#unmark-post').replaceWith('<a class="text-body-secondary m-3" type="button" id="mark-post" data-postid="' + postid + '" data-userid="' + userid + '" data-bs-custom-class="themed-tooltip" data-bs-toggle="tooltip" data-bs-title="Mark this post"><i class="bi bi-bookmark-plus" style="font-size:1.5rem"></i></a>');
                  // Initialize tooltip on new button
                  $('#mark-post').tooltip();
              } else {
                  alert(response.message);
              }
          }
      });
  });

  $(document).on('click', '.delete-subscriber', function(event) {
    event.preventDefault();
    var id = $(this).data('subscriber-id');

    $.ajax({
        type: 'POST',
        url: '/delete_subscriber/' + id,
        success: function(response) {
            if (response.status === 'success') {
                // Hide modal and reload the page
                $('#confirmationModal').modal('hide');
                window.location.reload();
            } else {
                alert(response.message);
            }
        }
    });
  });

  $(document).on('click', '.delete-comment', function(event) {
    event.preventDefault();
    var id = $(this).data('comment-id');

    $.ajax({
        type: 'POST',
        url: '/delete_comment/' + id,
        success: function(response) {
            if (response.status === 'success') {
                // Reload the page or update the subscriber list
                window.location.reload(); // or update subscriber list using JavaScript
            } else {
                alert(response.message);
            }
        }
    });
  });

  $(document).on('click', '.delete-post', function(event) {
    event.preventDefault();
    var id = $(this).data('post-id');

    $.ajax({
        type: 'POST',
        url: '/delete_post/' + id,
        success: function(response) {
            if (response.status === 'success') {
                // Hide modal and reload the page
                $('#confirmationModal').modal('hide');
                window.location.reload();
            } else {
                alert(response.message);
            }
        }
    });
  });
});





function showImageUpload() {
  const categoryValue = document.getElementById('fc-category').value
  const fileValue = document.getElementById('fc-file').value
  const urlValue = document.getElementById('fc-url').value

  document.getElementById("file-upload-card").style.display = "none";
  document.getElementById("image-upload-card").style.display = "block";

  document.getElementById("li-category").innerHTML = `<b> Category:- </b>  ${categoryValue}`
  document.getElementById("li-file").innerHTML = `<b> HTML file:- </b>  ${fileValue.replace('C:\\fakepath\\','')}`
  document.getElementById("li-url").innerHTML = `<b> URL:- </b>  ${urlValue}`
}

function showFileUpload() {
  document.getElementById("image-upload-card").style.display = "none";
  document.getElementById("file-upload-card").style.display = "block";
}





const carousels = document.querySelectorAll(".carousel");
// If a user hasn't opted in for reduced motion, then we add the animation
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  addAnimation();
}
function addAnimation() {
  carousels.forEach((carousel) => {
    // add data-animated="true" to every `.carousel` on the page
    carousel.setAttribute("data-animated", true);

    // Make an array from the elements within `.carousel-inner`
    const carouselInner = carousel.querySelector(".carousel__inner");
    const carouselContent = Array.from(carouselInner.children);

    // For each item in the array, clone it
    // add aria-hidden to it
    // add it into the `.carousel-inner`
    carouselContent.forEach((item) => {
      const duplicatedItem = item.cloneNode(true);
      duplicatedItem.setAttribute("aria-hidden", true);
      carouselInner.appendChild(duplicatedItem);
    });
  });
}





// Get all share buttons
const shareButtons = document.querySelectorAll('.share-button');
// Add click event listener to each button
shareButtons.forEach(button => {
   button.addEventListener('click', () => {
      // Get the URL of the current page
      const url = window.location.href;

      // Get the social media platform from the button's class name
      const platform = button.classList[1];

      // Set the URL to share based on the social media platform
      let shareUrl;
      switch (platform) {
        case 'whatsapp':
        shareUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(url)}`;
        break;
        case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
        break;
        case 'x':
        shareUrl = `https://x.com/share?url=${encodeURIComponent(url)}`;
        break;
        case 'threads':
        shareUrl = `https://www.threads.net/intent/post?text=${encodeURIComponent(url)}`;
        break;
        case 'copy':
        navigator.clipboard.writeText(url);        
        break;
        case 'mail' :
        button.setAttribute("href", `mailto:?subject=Check out this post on Shetty777!&body=${url}`);
        break;
      }

      // Open a new window to share the URL
      if (shareUrl) {
        window.open(shareUrl, '_blank');
      }
   });
});
