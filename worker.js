export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 健康检查接口
    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          message: "Service is running",
        }),
        {
          headers: {
            "content-type": "application/json",
          },
        }
      );
    }

    // 默认响应
    return new Response(
      JSON.stringify({
        status: "ok",
        message: "QQ Bot service is running",
      }),
      {
        headers: {
          "content-type": "application/json",
        },
      }
    );
  },

  async scheduled(event, env, ctx) {
    // 这里可以添加定时任务
    console.log("Scheduled task running");
  },
};
