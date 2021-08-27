import random
from django.db.models import Q, Count
from utils.api import APIView
from account.decorators import check_contest_permission
from ..models import ProblemTag, Problem, ProblemRuleType
from ..serializers import ProblemSerializer, TagSerializer, ProblemSafeSerializer
from contest.models import ContestRuleType
import logging
logger = logging.getLogger(__name__)

class ProblemTagAPI(APIView):
    logger.debug('-1 debug ProblemTagAPI')
    logger.info('-1 info ProblemTagAPI')
    # logger.error('-1 error ProblemTagAPI')
    print('-1 print ProblemTagAPI')
    def get(self, request):
        qs = ProblemTag.objects
        keyword = request.GET.get("keyword")
        logger.debug('0 debug')
        logger.info('0 info')
        # logger.error('0 error')
        print('0 print')
        if keyword:
            qs = ProblemTag.objects.filter(name__icontains=keyword)
        tags = qs.annotate(problem_count=Count("problem")).filter(problem_count__gt=0)
        return self.success(TagSerializer(tags, many=True).data)


class PickOneAPI(APIView):
    def get(self, request):
        problems = Problem.objects.filter(contest_id__isnull=True, visible=True)
        count = problems.count()
        if count == 0:
            return self.error("No problem to pick")
        return self.success(problems[random.randint(0, count - 1)]._id)


class ProblemAPI(APIView):
    @staticmethod
    def _add_problem_status(request, queryset_values):
        logger.debug('1 debug add_problem_status')
        # logger.info('1 info add_problem_status')
        # logger.error('1 error add_problem_status')
        print('1 print add_problem_status')
        if request.user.is_authenticated:
            profile = request.user.userprofile
            acm_problems_status = profile.acm_problems_status.get("problems", {})
            oi_problems_status = profile.oi_problems_status.get("problems", {})
            # paginate data
            results = queryset_values.get("results")
            logger.debug('2 debug')
            # logger.info('2 info')
            # logger.error('2 error')
            print('2 print')
            if results is not None:
                problems = results
            else:
                problems = [queryset_values, ]
            for problem in problems:
                if problem["rule_type"] == ProblemRuleType.ACM:
                    problem["my_status"] = acm_problems_status.get(str(problem["id"]), {}).get("status")
                else:
                    problem["my_status"] = oi_problems_status.get(str(problem["id"]), {}).get("status")

    def get(self, request):
        # 问题详情页
        logger.debug('3 debug get')
        # logger.info('3 info get')
        # logger.error('3 error get')
        print('3 print get')
        logger.debug('=====request=====')
        logger.debug(request)
        problem_id = request.GET.get("problem_id")
        logger.debug('=====problem_id=====')
        logger.debug(problem_id)
        if problem_id:
            logger.debug('4 debug')
            # logger.info('4 info')
            # logger.error('4 error')
            print('4 print')
            try:
                problem = Problem.objects.select_related("created_by") \
                    .get(_id=problem_id, contest_id__isnull=True, visible=True)
                logger.debug('=====problem=====')
                logger.debug(type(problem))
                problem_data2 = ProblemSerializer(problem)
                problem_data = ProblemSerializer(problem).data
                logger.debug('=====problem_data2=====')
                logger.debug(problem_data2)
                logger.debug('=====problem_data=====')
                logger.debug(problem_data)
                self._add_problem_status(request, problem_data)
                return self.success(problem_data)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist")

        limit = request.GET.get("limit")
        if not limit:
            return self.error("Limit is needed")

        problems = Problem.objects.select_related("created_by").filter(contest_id__isnull=True, visible=True)
        # 按照标签筛选
        tag_text = request.GET.get("tag")
        if tag_text:
            problems = problems.filter(tags__name=tag_text)

        # 搜索的情况
        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))

        # 难度筛选
        difficulty = request.GET.get("difficulty")
        if difficulty:
            problems = problems.filter(difficulty=difficulty)
        # 根据profile 为做过的题目添加标记
        data = self.paginate_data(request, problems, ProblemSerializer)
        self._add_problem_status(request, data)
        logger.debug('5 debug')
        # logger.info('5 info')
        # logger.error('5 error')
        print('5 print')
        return self.success(data)


class ContestProblemAPI(APIView):
    def _add_problem_status(self, request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            if self.contest.rule_type == ContestRuleType.ACM:
                problems_status = profile.acm_problems_status.get("contest_problems", {})
            else:
                problems_status = profile.oi_problems_status.get("contest_problems", {})
            for problem in queryset_values:
                problem["my_status"] = problems_status.get(str(problem["id"]), {}).get("status")

    @check_contest_permission(check_type="problems")
    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by").get(_id=problem_id,
                                                                           contest=self.contest,
                                                                           visible=True)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist.")
            if self.contest.problem_details_permission(request.user):
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, [problem_data, ])
            else:
                problem_data = ProblemSafeSerializer(problem).data
            return self.success(problem_data)

        contest_problems = Problem.objects.select_related("created_by").filter(contest=self.contest, visible=True)
        if self.contest.problem_details_permission(request.user):
            data = ProblemSerializer(contest_problems, many=True).data
            self._add_problem_status(request, data)
        else:
            data = ProblemSafeSerializer(contest_problems, many=True).data
        return self.success(data)
