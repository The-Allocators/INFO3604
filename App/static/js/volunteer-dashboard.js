document.addEventListener('DOMContentLoaded', function() {
  // Auto-refresh dashboard every 5 minutes
  const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes in milliseconds
  
  // Set up timer for automatic refresh
  setInterval(function() {
      refreshDashboard();
  }, REFRESH_INTERVAL);
  
  // Also add a manual refresh button if it exists
  const refreshButton = document.getElementById('refreshDashboard');
  if (refreshButton) {
      refreshButton.addEventListener('click', function(e) {
          e.preventDefault();
          refreshDashboard();
      });
  }
});

function refreshDashboard() {
  // Show loading indicator if it exists
  const loadingIndicator = document.getElementById('loadingIndicator');
  if (loadingIndicator) {
      loadingIndicator.style.display = 'block';
  }
  
  // Reload the page to get fresh data
  window.location.reload();
}